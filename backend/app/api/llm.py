# app/api/llm.py
# LLM API 路由
#
# 功能说明：
# 1. 提供 LLM 测试接口
# 2. 支持普通对话和流式输出
# 3. 需要用户认证
#
# API 列表：
# ┌─────────────────────────────────────────────────────────────┐
# │  方法  │  路径                    │  说明                   │
# ├────────┼─────────────────────────┼────────────────────────┤
# │  POST  │  /api/llm/chat          │  普通对话               │
# │  POST  │  /api/llm/stream        │  流式对话（SSE）        │
# │  POST  │  /api/llm/classify      │  意图分类               │
# └─────────────────────────────────────────────────────────────┘

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.core.logging import get_logger
from app.models.user import User
from app.llm.gateway import llm_gateway
from app.llm.prompts import render_prompt


# 获取当前模块的 logger
logger = get_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/llm", tags=["LLM"])


# ==================== 请求/响应 Schema ====================

class ChatRequest(BaseModel):
    """
    对话请求模式

    属性：
        message: 用户消息内容
        system_prompt: 可选的系统提示词
        model: 可选的模型名称
        temperature: 可选的温度参数
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User message",
        example="Hello, please introduce yourself"
    )

    system_prompt: Optional[str] = Field(
        None,
        max_length=5000,
        description="System prompt (optional)",
        example="You are a helpful assistant"
    )

    model: Optional[str] = Field(
        None,
        description="Model to use (optional)",
        example="claude-sonnet-4-20250514"
    )

    temperature: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Temperature, 0-1 (optional)",
        example=0.7
    )


class ChatResponse(BaseModel):
    """
    对话响应模式

    属性：
        response: AI 的响应内容
        model: 使用的模型
    """
    response: str = Field(..., description="AI response")
    model: str = Field(..., description="Model used")


class ClassifyRequest(BaseModel):
    """
    意图分类请求模式

    属性：
        content: 要分类的内容
    """
    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Content to classify",
        example="What is the price of product A?"
    )


class ClassifyResponse(BaseModel):
    """
    意图分类响应模式

    属性：
        intent: 识别的意图类型
        confidence: 置信度
        keywords: 关键词
        raw_response: 原始 LLM 响应
    """
    intent: str = Field(..., description="Intent type")
    confidence: float = Field(..., description="Confidence score")
    keywords: list = Field(default=[], description="Keywords")
    raw_response: str = Field(..., description="Raw LLM response")


# ==================== API 路由 ====================

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat",
    description="Send message and get AI response, requires authentication"
)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """
    普通对话接口

    发送一条消息，获取完整的 AI 响应

    Args:
        request: 对话请求（消息内容、系统提示等）
        current_user: 当前用户（通过认证获取）

    Returns:
        ChatResponse: AI 的响应

    请求示例：
        POST /api/llm/chat
        Headers: Authorization: Bearer <token>
        Body:
        {
            "message": "你好，请介绍一下自己"
        }

    响应示例：
        {
            "response": "你好！我是 Concord AI 智能助手...",
            "model": "claude-sonnet-4-20250514"
        }
    """
    logger.info(f"用户 {current_user.email} 发起对话请求")

    try:
        # 使用默认系统提示词（如果没有指定）
        if request.system_prompt:
            system = request.system_prompt
        else:
            system = await render_prompt("chat_agent")

        # 调用 LLM Gateway
        response = await llm_gateway.chat(
            message=request.message,
            system=system,
            model=request.model,
            temperature=request.temperature,
        )

        logger.info(f"对话完成，响应长度: {len(response.content)}")

        # 从响应中获取实际使用的模型
        model_used = response.model or request.model or "default"

        return ChatResponse(
            response=response.content,
            model=model_used
        )

    except Exception as e:
        logger.error(f"对话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM 调用失败: {str(e)}"
        )


@router.post(
    "/stream",
    summary="Chat Stream",
    description="Send message and get streaming response (SSE), requires authentication"
)
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    流式对话接口（Server-Sent Events）

    发送一条消息，逐字返回 AI 响应
    适用于需要实时显示输出的场景（如 Chatbox）

    Args:
        request: 对话请求
        current_user: 当前用户

    Returns:
        StreamingResponse: SSE 流式响应

    请求示例：
        POST /api/llm/stream
        Headers: Authorization: Bearer <token>
        Body:
        {
            "message": "写一首关于春天的诗"
        }

    响应（SSE 格式）：
        data: 春

        data: 风

        data: 拂

        data: 面

        ...

    前端使用示例：
        const eventSource = new EventSource('/api/llm/stream');
        eventSource.onmessage = (event) => {
            console.log(event.data);  // 逐字输出
        };
    """
    logger.info(f"用户 {current_user.email} 发起流式对话请求")

    async def generate():
        """
        生成 SSE 事件流

        SSE 格式说明：
        - 每个事件以 "data: " 开头
        - 每个事件以两个换行符结束
        - 特殊事件 "[DONE]" 表示结束
        """
        try:
            # 使用默认系统提示词
            if request.system_prompt:
                system = request.system_prompt
            else:
                system = await render_prompt("chat_agent")

            # 调用 LLM Gateway 流式接口
            async for chunk in llm_gateway.chat_stream(
                message=request.message,
                system=system,
                model=request.model,
                temperature=request.temperature,
            ):
                # 发送 SSE 事件
                # 格式：data: <内容>\n\n
                yield f"data: {chunk}\n\n"

            # 发送结束标记
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"流式对话失败: {e}")
            # 发送错误信息
            yield f"data: [ERROR] {str(e)}\n\n"

    # 返回 SSE 响应
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post(
    "/classify",
    response_model=ClassifyResponse,
    summary="Classify Intent",
    description="Analyze text content intent, requires authentication"
)
async def classify_intent(
    request: ClassifyRequest,
    current_user: User = Depends(get_current_user),
) -> ClassifyResponse:
    """
    意图分类接口

    分析输入内容的意图类型（询价、订单、支持等）

    Args:
        request: 分类请求（要分析的内容）
        current_user: 当前用户

    Returns:
        ClassifyResponse: 分类结果

    支持的意图类型：
        - inquiry: 询价
        - order: 订单
        - support: 支持
        - feedback: 反馈
        - general: 一般
        - unknown: 未知

    请求示例：
        POST /api/llm/classify
        Headers: Authorization: Bearer <token>
        Body:
        {
            "content": "请问产品A的价格是多少？"
        }

    响应示例：
        {
            "intent": "inquiry",
            "confidence": 0.95,
            "keywords": ["价格", "产品A"],
            "raw_response": "{...}"
        }
    """
    logger.info(f"用户 {current_user.email} 请求意图分类")

    try:
        # 使用新的 Prompt 系统
        # intent_classifier Prompt 已经包含了系统提示和用户消息
        prompt = await render_prompt("intent_classifier", content=request.content)

        # 调用 LLM Gateway（使用较低的 temperature 以获得更稳定的输出）
        response = await llm_gateway.chat(
            message=prompt,
            system=None,  # Prompt 中已包含指令
            temperature=0.2,  # 降低温度以获得更确定的结果
        )

        logger.debug(f"分类原始响应: {response.content}")

        # 解析 JSON 响应
        import json
        try:
            result = json.loads(response.content)
            return ClassifyResponse(
                intent=result.get("intent", "unknown"),
                confidence=result.get("confidence", 0.0),
                keywords=result.get("keywords", []),
                raw_response=response.content
            )
        except json.JSONDecodeError:
            # 如果无法解析 JSON，返回原始响应
            logger.warning(f"无法解析分类响应: {response.content}")
            return ClassifyResponse(
                intent="unknown",
                confidence=0.0,
                keywords=[],
                raw_response=response.content
            )

    except Exception as e:
        logger.error(f"意图分类失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"意图分类失败: {str(e)}"
        )
