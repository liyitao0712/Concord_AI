# app/agents/router_agent.py
# 消息路由 Agent
#
# 功能说明：
# 1. 作为所有消息的统一入口
# 2. 从数据库加载意图定义
# 3. 使用 LLM 进行意图分类
# 4. 返回路由结果（匹配的意图 + 处理方式）
# 5. 可建议新意图（当没有匹配时）
#
# 使用方法：
#   from app.agents.router_agent import router_agent
#
#   result = await router_agent.route(event)
#   if result.action == "agent":
#       # 使用 Agent 处理
#   elif result.action == "workflow":
#       # 启动 Temporal Workflow

import json
import re
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.database import async_session_maker
from app.models.intent import Intent
from app.models.prompt import Prompt
from app.schemas.event import UnifiedEvent
from app.llm.gateway import llm_gateway
from app.agents.base import BaseAgent
from app.agents.registry import register_agent

logger = get_logger(__name__)


# 默认 Prompt（数据库无数据时的 fallback）
DEFAULT_ROUTER_PROMPT = """你是一个意图分类专家，负责分析消息的意图。

## 已有意图列表
{intents_json}

## 待分类消息
来源: {source}
{subject_line}内容:
{content}

## 任务
1. 判断这条消息属于哪个已有意图
2. 如果没有合适的意图匹配，请建议新增意图

## 返回格式（纯 JSON，不要 markdown）
{{
  "matched_intent": "意图的name字段值" | null,
  "confidence": 0.0-1.0,
  "reasoning": "判断理由（简短）",
  "new_suggestion": {{
    "name": "建议的英文名（小写下划线）",
    "label": "建议的中文名",
    "description": "这类消息的特征描述",
    "suggested_handler": "agent 或 workflow"
  }} | null
}}

注意：
1. confidence 表示你对匹配结果的确信程度
2. 如果 confidence < 0.6，应该考虑建议新意图
3. new_suggestion 只在没有合适匹配时提供
4. 只输出 JSON，不要添加任何其他内容"""


@dataclass
class NewIntentSuggestion:
    """AI 建议的新意图"""
    name: str
    label: str
    description: str
    suggested_handler: str = "agent"
    examples: List[str] = field(default_factory=list)


@dataclass
class RouteResult:
    """路由结果"""
    # 匹配的意图
    intent: str
    intent_label: str = ""
    confidence: float = 0.0
    reasoning: str = ""

    # 处理方式
    action: str = "agent"  # "agent" | "workflow"
    handler_config: dict = field(default_factory=dict)
    workflow_name: Optional[str] = None

    # 是否需要升级（人工审批）
    needs_escalation: bool = False
    escalation_reason: Optional[str] = None

    # 新意图建议
    new_suggestion: Optional[NewIntentSuggestion] = None


@register_agent
class RouterAgent(BaseAgent):
    """
    消息路由 Agent

    统一消息入口，负责：
    1. 加载意图定义
    2. 使用 LLM 分类
    3. 返回路由决策
    """

    name = "router_agent"
    description = "消息路由分类器，决定消息应该由谁处理"

    def __init__(self):
        super().__init__()
        self._intents_cache: List[Intent] = []
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = 60  # 缓存 60 秒
        self._prompt_cache: Optional[str] = None
        self._prompt_cache_time: Optional[datetime] = None

    async def _load_prompt(self, session: Optional[AsyncSession] = None) -> str:
        """
        从数据库加载 Prompt 模板

        带缓存，避免频繁查询数据库
        """
        now = datetime.utcnow()

        # 检查缓存
        if (
            self._prompt_cache
            and self._prompt_cache_time
            and (now - self._prompt_cache_time).total_seconds() < self._cache_ttl
        ):
            return self._prompt_cache

        # 查询数据库
        async def do_load(sess: AsyncSession) -> Optional[str]:
            result = await sess.execute(
                select(Prompt.content)
                .where(Prompt.name == "router_agent")
                .where(Prompt.is_active == True)
            )
            row = result.scalar_one_or_none()
            return row

        try:
            if session:
                prompt_content = await do_load(session)
            else:
                async with async_session_maker() as sess:
                    prompt_content = await do_load(sess)

            if prompt_content:
                # 数据库中的 prompt 使用 {{var}} 格式，转换为 {var} 格式
                self._prompt_cache = prompt_content.replace("{{", "{").replace("}}", "}")
                self._prompt_cache_time = now
                logger.debug("[RouterAgent] 已从数据库加载 Prompt")
                return self._prompt_cache
        except Exception as e:
            logger.warning(f"[RouterAgent] 加载 Prompt 失败: {e}")

        # 使用默认 Prompt
        logger.debug("[RouterAgent] 使用默认 Prompt")
        return DEFAULT_ROUTER_PROMPT

    async def _load_intents(self, session: Optional[AsyncSession] = None) -> List[Intent]:
        """
        从数据库加载意图定义

        带缓存，避免频繁查询数据库
        """
        now = datetime.utcnow()

        # 检查缓存
        if (
            self._intents_cache
            and self._cache_time
            and (now - self._cache_time).total_seconds() < self._cache_ttl
        ):
            return self._intents_cache

        # 查询数据库
        async def do_load(sess: AsyncSession) -> List[Intent]:
            result = await sess.execute(
                select(Intent)
                .where(Intent.is_active == True)
                .order_by(Intent.priority.desc())
            )
            return list(result.scalars().all())

        if session:
            intents = await do_load(session)
        else:
            async with async_session_maker() as sess:
                intents = await do_load(sess)

        # 更新缓存
        self._intents_cache = intents
        self._cache_time = now

        logger.debug(f"[RouterAgent] 加载了 {len(intents)} 个意图")
        return intents

    def _build_intents_json(self, intents: List[Intent]) -> str:
        """构建意图列表 JSON（给 LLM）"""
        intent_list = []
        for intent in intents:
            intent_list.append({
                "name": intent.name,
                "label": intent.label,
                "description": intent.description,
                "keywords": intent.keywords or [],
                "examples": (intent.examples or [])[:3],  # 最多 3 个示例
            })
        return json.dumps(intent_list, ensure_ascii=False, indent=2)

    async def _classify(
        self,
        event: UnifiedEvent,
        intents: List[Intent],
        session: Optional[AsyncSession] = None,
    ) -> dict:
        """
        使用 LLM 进行意图分类

        Returns:
            dict: LLM 返回的分类结果
        """
        # 从数据库加载 Prompt 模板
        prompt_template = await self._load_prompt(session)

        # 构建 Prompt
        intents_json = self._build_intents_json(intents)

        # 处理主题行（邮件有主题）
        subject_line = ""
        if event.metadata and event.metadata.get("subject"):
            subject_line = f"主题: {event.metadata['subject']}\n"

        prompt = prompt_template.format(
            intents_json=intents_json,
            source=event.source or "unknown",
            subject_line=subject_line,
            content=event.content[:2000],  # 限制长度
        )

        # 调用 LLM
        try:
            response = await llm_gateway.chat(
                message=prompt,
                system="你是意图分类专家，只输出 JSON 格式的分类结果。",
                temperature=0.3,  # 低温度，更确定性
            )

            # 解析 JSON
            content = response.content.strip()
            # 移除可能的 markdown 代码块
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\n?", "", content)
                content = re.sub(r"\n?```$", "", content)

            result = json.loads(content)
            logger.info(
                f"[RouterAgent] 分类结果: intent={result.get('matched_intent')}, "
                f"confidence={result.get('confidence')}"
            )
            return result

        except json.JSONDecodeError as e:
            logger.error(f"[RouterAgent] JSON 解析失败: {e}, content={response.content[:200]}")
            return {
                "matched_intent": "other",
                "confidence": 0.5,
                "reasoning": "LLM 返回格式错误，使用兜底意图",
                "new_suggestion": None,
            }
        except Exception as e:
            logger.error(f"[RouterAgent] LLM 调用失败: {e}")
            return {
                "matched_intent": "other",
                "confidence": 0.5,
                "reasoning": f"分类失败: {str(e)}",
                "new_suggestion": None,
            }

    def _should_escalate(self, intent: Intent, event: UnifiedEvent) -> tuple[bool, str]:
        """
        判断是否需要升级到 Workflow（人工审批）

        Returns:
            tuple[bool, str]: (是否升级, 原因)
        """
        rules = intent.escalation_rules
        if not rules:
            return False, ""

        # 规则：always = true
        if rules.get("always"):
            return True, "此意图总是需要人工处理"

        # 规则：包含特定关键词
        keywords = rules.get("keywords", [])
        if keywords:
            content = event.content.lower()
            for kw in keywords:
                if kw.lower() in content:
                    return True, f"包含关键词: {kw}"

        # 规则：金额超过阈值（简单实现，后续可以用 NER）
        amount_threshold = rules.get("amount_gt")
        if amount_threshold:
            # 简单正则提取数字
            numbers = re.findall(r"\d+(?:\.\d+)?", event.content)
            for num_str in numbers:
                try:
                    num = float(num_str)
                    if num > amount_threshold:
                        return True, f"金额 {num} 超过阈值 {amount_threshold}"
                except ValueError:
                    pass

        return False, ""

    async def route(
        self,
        event: UnifiedEvent,
        session: Optional[AsyncSession] = None,
    ) -> RouteResult:
        """
        路由消息

        这是主入口方法，接收 UnifiedEvent，返回路由决策。

        Args:
            event: 统一事件
            session: 可选的数据库会话

        Returns:
            RouteResult: 路由结果
        """
        logger.info(f"[RouterAgent] 开始路由: event_id={event.event_id}, source={event.source}")

        # 1. 加载意图
        intents = await self._load_intents(session)

        # 2. LLM 分类
        classification = await self._classify(event, intents, session)

        matched_name = classification.get("matched_intent")
        confidence = classification.get("confidence", 0.0)
        reasoning = classification.get("reasoning", "")

        # 3. 查找匹配的意图
        matched_intent: Optional[Intent] = None
        if matched_name:
            for intent in intents:
                if intent.name == matched_name:
                    matched_intent = intent
                    break

        # 4. 没有匹配，使用 "other" 兜底
        if not matched_intent:
            for intent in intents:
                if intent.name == "other":
                    matched_intent = intent
                    break

        # 5. 仍然没有，创建默认结果
        if not matched_intent:
            logger.warning("[RouterAgent] 没有找到任何意图，包括 other")
            return RouteResult(
                intent="other",
                intent_label="其他",
                confidence=0.0,
                reasoning="没有配置任何意图",
                action="agent",
                handler_config={"agent_name": "ChatAgent"},
            )

        # 6. 检查是否需要升级
        needs_escalation, escalation_reason = self._should_escalate(matched_intent, event)

        # 7. 构建结果
        result = RouteResult(
            intent=matched_intent.name,
            intent_label=matched_intent.label,
            confidence=confidence,
            reasoning=reasoning,
            action=matched_intent.default_handler,
            handler_config=matched_intent.handler_config or {},
            needs_escalation=needs_escalation,
            escalation_reason=escalation_reason,
        )

        # 如果需要升级，使用升级 Workflow
        if needs_escalation and matched_intent.escalation_workflow:
            result.action = "workflow"
            result.workflow_name = matched_intent.escalation_workflow
        elif matched_intent.default_handler == "workflow":
            result.workflow_name = matched_intent.handler_config.get("workflow_name")

        # 8. 处理新意图建议
        new_suggestion = classification.get("new_suggestion")
        if new_suggestion and confidence < 0.6:
            result.new_suggestion = NewIntentSuggestion(
                name=new_suggestion.get("name", "unknown"),
                label=new_suggestion.get("label", "未知"),
                description=new_suggestion.get("description", ""),
                suggested_handler=new_suggestion.get("suggested_handler", "agent"),
            )
            logger.info(f"[RouterAgent] AI 建议新意图: {result.new_suggestion.name}")

        logger.info(
            f"[RouterAgent] 路由完成: intent={result.intent}, "
            f"action={result.action}, escalation={result.needs_escalation}"
        )

        return result

    async def route_text(
        self,
        content: str,
        source: str = "web",
        metadata: Optional[dict] = None,
    ) -> RouteResult:
        """
        简化的路由方法，直接传入文本

        用于测试或简单场景
        """
        from uuid import uuid4

        event = UnifiedEvent(
            event_id=str(uuid4()),
            event_type="message",
            source=source,
            content=content,
            metadata=metadata or {},
        )
        return await self.route(event)

    async def process_output(self, state: dict) -> dict:
        """
        处理输出（实现抽象方法）

        RouterAgent 不使用标准的 BaseAgent 工作流，
        而是直接使用 route() 方法，所以这里只是简单返回状态。
        """
        return state

    def clear_cache(self) -> None:
        """清除意图和 Prompt 缓存"""
        self._intents_cache = []
        self._cache_time = None
        self._prompt_cache = None
        self._prompt_cache_time = None
        logger.info("[RouterAgent] 缓存已清除")


# 全局单例
router_agent = RouterAgent()
