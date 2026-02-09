# app/services/tts_service.py
# TTS 语音合成服务
#
# 功能说明：
# 1. 支持多 Provider：Edge-TTS（免费）、OpenAI TTS、阿里云 DashScope TTS
# 2. 统一接口，根据 provider 参数分发到对应实现
# 3. 返回 MP3 音频二进制数据

import io
import os
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# provider → 环境变量名 → 数据库 provider 名
_KEY_MAP = {
    "openai": ("OPENAI_API_KEY", "openai"),
    "dashscope": ("DASHSCOPE_API_KEY", "qwen"),
}


async def _get_api_key(provider: str) -> str:
    """获取 API Key：先查环境变量，没有则从数据库 llm_model_configs 读取"""
    env_name, db_provider = _KEY_MAP[provider]

    # 1. 环境变量已有，直接用
    key = os.environ.get(env_name)
    if key:
        return key

    # 2. 从数据库读取
    from sqlalchemy import select
    from app.core.database import async_session_maker
    from app.models.llm_model_config import LLMModelConfig

    async with async_session_maker() as db:
        result = await db.execute(
            select(LLMModelConfig.api_key).where(
                LLMModelConfig.provider == db_provider,
                LLMModelConfig.is_configured == True,
                LLMModelConfig.api_key.isnot(None),
            ).limit(1)
        )
        row = result.scalar_one_or_none()

    if not row:
        raise ValueError(
            f"{provider} API Key 未配置。请在「LLM 模型管理」中添加一个 "
            f"{db_provider} 模型并填入 API Key"
        )

    # 缓存到环境变量，下次无需查库
    os.environ[env_name] = row
    return row


async def synthesize(
    text: str,
    provider: str = "edge-tts",
    voice: Optional[str] = None,
    speed: float = 1.0,
) -> bytes:
    """
    文本转语音

    Args:
        text: 要合成的文本
        provider: TTS 引擎（edge-tts / openai / dashscope）
        voice: 语音 ID（不传则使用各 provider 的默认中文语音）
        speed: 语速倍率，默认 1.0

    Returns:
        bytes: MP3 音频数据
    """
    if provider == "edge-tts":
        return await _synthesize_edge_tts(text, voice, speed)
    elif provider == "openai":
        return await _synthesize_openai(text, voice, speed)
    elif provider == "dashscope":
        return await _synthesize_dashscope(text, voice)
    else:
        raise ValueError(f"不支持的 TTS 引擎: {provider}")


async def _synthesize_edge_tts(
    text: str,
    voice: Optional[str] = None,
    speed: float = 1.0,
) -> bytes:
    """Edge-TTS（微软免费语音）"""
    import edge_tts

    voice = voice or "zh-CN-XiaoxiaoNeural"
    # edge-tts 语速格式："+10%" 或 "-10%"
    rate_pct = round((speed - 1.0) * 100)
    rate_str = f"{rate_pct:+d}%" if rate_pct != 0 else "+0%"

    communicate = edge_tts.Communicate(text, voice, rate=rate_str)

    buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buffer.write(chunk["data"])

    audio_data = buffer.getvalue()
    if not audio_data:
        raise RuntimeError("Edge-TTS 未返回音频数据")

    logger.info(f"[TTS] Edge-TTS 合成完成, voice={voice}, 文本长度={len(text)}, 音频大小={len(audio_data)} bytes")
    return audio_data


async def _synthesize_openai(
    text: str,
    voice: Optional[str] = None,
    speed: float = 1.0,
) -> bytes:
    """OpenAI TTS"""
    api_key = await _get_api_key("openai")

    import httpx

    voice = voice or "nova"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "tts-1",
                "input": text,
                "voice": voice,
                "speed": speed,
                "response_format": "mp3",
            },
        )

        if response.status_code != 200:
            error_detail = response.text[:200]
            raise RuntimeError(f"OpenAI TTS 请求失败 ({response.status_code}): {error_detail}")

        audio_data = response.content
        logger.info(f"[TTS] OpenAI 合成完成, voice={voice}, 文本长度={len(text)}, 音频大小={len(audio_data)} bytes")
        return audio_data


async def _synthesize_dashscope(
    text: str,
    voice: Optional[str] = None,
) -> bytes:
    """阿里云 DashScope TTS（CosyVoice SDK）"""
    api_key = await _get_api_key("dashscope")

    import dashscope
    from dashscope.audio.tts_v2 import SpeechSynthesizer

    dashscope.api_key = api_key
    voice = voice or "longxiaochun"

    # SDK 同步调用，在线程池中执行避免阻塞事件循环
    import asyncio
    loop = asyncio.get_event_loop()
    audio_data = await loop.run_in_executor(
        None,
        lambda: SpeechSynthesizer(model="cosyvoice-v1", voice=voice).call(text),
    )

    if not audio_data:
        raise RuntimeError("DashScope TTS 未返回音频数据")

    logger.info(f"[TTS] DashScope 合成完成, voice={voice}, 文本长度={len(text)}, 音频大小={len(audio_data)} bytes")
    return audio_data
