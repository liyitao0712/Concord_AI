# app/llm/prompts/manager.py
# Prompt 管理器
#
# 功能：
# 1. 从数据库加载 Prompt（优先）
# 2. 回退到默认值
# 3. 缓存机制
# 4. 变量渲染

from typing import Optional
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.database import get_db
from app.models.prompt import Prompt
from app.llm.prompts.defaults import DEFAULT_PROMPTS, get_default_prompt

logger = get_logger(__name__)


class PromptManager:
    """
    Prompt 管理器

    负责加载、缓存、渲染 Prompt 模板

    使用方法：
        manager = PromptManager()

        # 获取 Prompt 内容
        content = await manager.get_prompt("intent_classifier")

        # 渲染 Prompt
        rendered = await manager.render("intent_classifier", content="用户消息...")

        # 刷新缓存
        await manager.refresh_cache("intent_classifier")
    """

    # 缓存过期时间（秒）
    CACHE_TTL = 300  # 5 分钟

    def __init__(self):
        self._cache: dict[str, dict] = {}
        self._cache_time: dict[str, datetime] = {}

    def _is_cache_valid(self, name: str) -> bool:
        """检查缓存是否有效"""
        if name not in self._cache:
            return False
        cache_time = self._cache_time.get(name)
        if not cache_time:
            return False
        return datetime.utcnow() - cache_time < timedelta(seconds=self.CACHE_TTL)

    async def get_prompt(
        self,
        name: str,
        *,
        use_cache: bool = True,
    ) -> Optional[str]:
        """
        获取 Prompt 内容

        Args:
            name: Prompt 名称
            use_cache: 是否使用缓存

        Returns:
            str: Prompt 内容，如果不存在返回 None
        """
        # 检查缓存
        if use_cache and self._is_cache_valid(name):
            return self._cache[name].get("content")

        # 从数据库加载
        prompt_data = await self._load_from_db(name)

        if prompt_data:
            self._cache[name] = prompt_data
            self._cache_time[name] = datetime.utcnow()
            return prompt_data.get("content")

        # 回退到默认值
        default = get_default_prompt(name)
        if default:
            logger.debug(f"[Prompt] 使用默认值: {name}")
            self._cache[name] = default
            self._cache_time[name] = datetime.utcnow()
            return default.get("content")

        logger.warning(f"[Prompt] 未找到: {name}")
        return None

    async def get_prompt_data(
        self,
        name: str,
        *,
        use_cache: bool = True,
    ) -> Optional[dict]:
        """
        获取完整的 Prompt 数据（包含元信息）

        Args:
            name: Prompt 名称
            use_cache: 是否使用缓存

        Returns:
            dict: Prompt 数据，包含 content, variables, model_hint 等
        """
        if use_cache and self._is_cache_valid(name):
            return self._cache[name]

        prompt_data = await self._load_from_db(name)

        if prompt_data:
            self._cache[name] = prompt_data
            self._cache_time[name] = datetime.utcnow()
            return prompt_data

        default = get_default_prompt(name)
        if default:
            self._cache[name] = default
            self._cache_time[name] = datetime.utcnow()
            return default

        return None

    async def render(
        self,
        name: str,
        **variables,
    ) -> Optional[str]:
        """
        渲染 Prompt 模板

        Args:
            name: Prompt 名称
            **variables: 模板变量

        Returns:
            str: 渲染后的 Prompt
        """
        content = await self.get_prompt(name)
        if not content:
            return None

        # 简单的模板替换
        result = content
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            result = result.replace(placeholder, str(value))

        return result

    async def _load_from_db(self, name: str) -> Optional[dict]:
        """从数据库加载 Prompt"""
        try:
            async for session in get_db():
                result = await session.execute(
                    select(Prompt).where(
                        Prompt.name == name,
                        Prompt.is_active == True,
                    )
                )
                prompt = result.scalar_one_or_none()

                if prompt:
                    logger.debug(f"[Prompt] 从数据库加载: {name} (v{prompt.version})")
                    return {
                        "content": prompt.content,
                        "variables": prompt.variables,
                        "model_hint": prompt.model_hint,
                        "category": prompt.category,
                        "version": prompt.version,
                    }
                return None
        except Exception as e:
            # 数据库不可用时，静默失败，使用默认值
            logger.debug(f"[Prompt] 数据库加载失败，使用默认值: {e}")
            return None

    async def refresh_cache(self, name: Optional[str] = None):
        """
        刷新缓存

        Args:
            name: 指定刷新的 Prompt 名称，为空则刷新全部
        """
        if name:
            if name in self._cache:
                del self._cache[name]
            if name in self._cache_time:
                del self._cache_time[name]
            logger.info(f"[Prompt] 缓存已刷新: {name}")
        else:
            self._cache.clear()
            self._cache_time.clear()
            logger.info("[Prompt] 全部缓存已刷新")

    async def init_defaults(self, session: AsyncSession):
        """
        初始化默认 Prompt 到数据库

        用于首次部署时填充默认值
        """
        for name, data in DEFAULT_PROMPTS.items():
            # 检查是否已存在
            result = await session.execute(
                select(Prompt).where(Prompt.name == name)
            )
            existing = result.scalar_one_or_none()

            if not existing:
                prompt = Prompt(
                    name=name,
                    display_name=data.get("display_name", name),
                    category=data.get("category", "general"),
                    content=data["content"],
                    variables=data.get("variables", {}),
                    description=data.get("description"),
                    model_hint=data.get("model_hint"),
                )
                session.add(prompt)
                logger.info(f"[Prompt] 初始化默认 Prompt: {name}")

        await session.commit()


# 全局单例
prompt_manager = PromptManager()


# 便捷函数
async def get_prompt(name: str, **kwargs) -> Optional[str]:
    """获取 Prompt 内容"""
    return await prompt_manager.get_prompt(name, **kwargs)


async def render_prompt(name: str, **variables) -> Optional[str]:
    """渲染 Prompt 模板"""
    return await prompt_manager.render(name, **variables)
