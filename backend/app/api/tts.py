# app/api/tts.py
# TTS 语音合成 API
#
# 功能说明：
# 1. POST /admin/tts/synthesize - 文本转语音，返回 MP3 音频流
# 2. 支持多 Provider 切换（edge-tts / openai / dashscope）

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.security import require_permission, DataScope
from app.services import tts_service
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/tts", tags=["TTS 语音合成"])


class TTSSynthesizeRequest(BaseModel):
    """语音合成请求"""
    text: str = Field(..., min_length=1, max_length=50000, description="要合成的文本")
    provider: str = Field("edge-tts", description="TTS 引擎: edge-tts / openai / dashscope")
    voice: Optional[str] = Field(None, description="语音 ID（不传使用默认中文语音）")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="语速倍率")


@router.post("/synthesize")
async def synthesize(
    request: TTSSynthesizeRequest,
    _: DataScope = Depends(require_permission("setting", "read")),
):
    """
    文本转语音

    将文本合成为 MP3 音频并返回。支持多个 TTS 引擎：
    - **edge-tts**：微软语音（免费，中文语音：zh-CN-XiaoxiaoNeural）
    - **openai**：OpenAI TTS（需配置 API Key，语音：nova）
    - **dashscope**：阿里云语音（需配置 DashScope Key，语音：longxiaochun）
    """
    logger.info(f"[TTS] 收到请求: provider={request.provider}, text_len={len(request.text)}, voice={request.voice}, speed={request.speed}")

    try:
        audio_data = await tts_service.synthesize(
            text=request.text,
            provider=request.provider,
            voice=request.voice,
            speed=request.speed,
        )

        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline",
                "Cache-Control": "no-cache",
            },
        )

    except ValueError as e:
        logger.warning(f"[TTS] ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        logger.warning(f"[TTS] ImportError: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"TTS 引擎依赖未安装: {e}。请运行 pip install edge-tts",
        )
    except Exception as e:
        logger.error(f"[TTS] 合成失败: provider={request.provider}, error={type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"语音合成失败: {str(e)}",
        )
