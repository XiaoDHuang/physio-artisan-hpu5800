"""
千问 / OpenAI TTS 语音合成适配器

封装 TTS 调用，支持两种路径：
- audio_speech: POST /audio/speech（OpenAI TTS 接口，返回音频字节）
- chat_audio_out: POST /chat/completions（多模态 audio output，兜底）

经 spike 验证：apiyi 网关 /audio/speech 可用（qwen3-omni-flash / tts-1）。
"""

import json
import logging
import time
from typing import Optional

import requests

from config.langgraph_config import langgraph_config as config

logger = logging.getLogger("tts")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    import os as _os
    _os.makedirs("logs", exist_ok=True)
    _fh = logging.FileHandler("logs/backend.log", encoding="utf-8")
    _fh.setLevel(logging.INFO)
    _fh.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(_fh)


class TTSError(Exception):
    """TTS 受控异常，路由层捕获后转 5xx。"""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


class TTSValidationError(Exception):
    """TTS 参数校验异常，路由层捕获后转 4xx。"""

    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


def _post_with_retry(method, url, **kwargs):
    """带 429 指数退避的 requests 调用。"""
    max_retries = 3
    delays = [1, 2, 3]
    for attempt in range(max_retries + 1):
        try:
            resp = requests.request(method, url, **kwargs)
            if resp.status_code == 429 and attempt < max_retries:
                delay = delays[attempt]
                logger.warning(f"TTS 被限流(429)，{delay}s 后重试({attempt + 1}/{max_retries})")
                time.sleep(delay)
                continue
            return resp
        except requests.RequestException:
            if attempt < max_retries:
                delay = delays[attempt]
                logger.warning(f"TTS 请求失败，{delay}s 后重试({attempt + 1}/{max_retries})")
                time.sleep(delay)
                continue
            raise
    raise TTSError("TTS 服务不可用（多次重试后仍失败）")


def _synthesize_via_audio_speech(text: str) -> bytes:
    """路径①：OpenAI TTS 接口。

    POST {base_url}/audio/speech
    JSON: {model, input, voice, response_format}
    返回: audio/mpeg 字节
    """
    base_url = config.TTS_BASE_URL.rstrip("/")
    url = f"{base_url}/audio/speech"

    payload = {
        "model": config.TTS_MODEL,
        "input": text,
        "voice": config.TTS_VOICE,
        "response_format": "mp3",
    }

    try:
        resp = _post_with_retry("POST", url,
            json=payload,
            headers={
                "Authorization": f"Bearer {config.TTS_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=60,
        )
    except requests.RequestException as e:
        logger.error(f"TTS audio_speech 请求失败: {e}")
        raise TTSError(f"TTS 服务请求失败: {e}") from e

    if not resp.ok:
        logger.error(f"TTS audio_speech 上游错误 {resp.status_code}: {resp.text[:300]}")
        raise TTSError(f"TTS 语音合成服务返回 {resp.status_code}")

    return resp.content


def _synthesize_via_chat_audio_out(text: str) -> bytes:
    """路径②：多模态 chat completions + audio output（兜底）。

    POST {base_url}/chat/completions
    JSON: {model, messages, modalities: ["audio"], audio: {voice, format}}
    返回: JSON 中提取 audio data（base64 → bytes）
    """
    base_url = config.TTS_BASE_URL.rstrip("/")
    url = f"{base_url}/chat/completions"

    payload = {
        "model": config.TTS_MODEL,
        "messages": [
            {
                "role": "user",
                "content": f"请用温暖、专业的语气朗读以下健康建议文本，输出语音：\n\n{text}",
            }
        ],
        "modalities": ["audio"],
        "audio": {
            "voice": config.TTS_VOICE,
            "format": "mp3",
        },
    }

    try:
        resp = _post_with_retry("POST", url,
            json=payload,
            headers={
                "Authorization": f"Bearer {config.TTS_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=60,
        )
    except requests.RequestException as e:
        logger.error(f"TTS chat_audio_out 请求失败: {e}")
        raise TTSError(f"TTS 服务请求失败: {e}") from e

    if not resp.ok:
        logger.error(f"TTS chat_audio_out 上游错误 {resp.status_code}: {resp.text[:300]}")
        raise TTSError(f"TTS 语音合成服务返回 {resp.status_code}")

    # 尝试从 chat completions 响应中提取 audio data
    try:
        body = resp.json()
        output = body["choices"][0]["message"].get("audio", {})
        data = output.get("data", "")
        if data:
            import base64
            return base64.b64decode(data)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        pass

    raise TTSError("TTS 音频输出解析失败：响应中未找到音频数据")


def synthesize_speech(text: str) -> bytes:
    """语音合成主入口。

    参数：
        text: 待合成文本（建议 ≤1000 字符）

    返回：
        音频字节（mp3 格式）

    异常：
        TTSError — 上游 TTS 调用失败
        TTSValidationError — 参数校验失败
    """
    if not text or not text.strip():
        raise TTSValidationError("文本为空")

    cleaned = text.strip()
    if len(cleaned) > config.TTS_MAX_CHARS:
        cleaned = cleaned[:config.TTS_MAX_CHARS]
        logger.warning(f"TTS 文本过长，截断至 {config.TTS_MAX_CHARS} 字符")

    # 路径①：audio/speech 标准端点
    try:
        audio_data = _synthesize_via_audio_speech(cleaned)
        if audio_data and len(audio_data) > 100:
            logger.info(f"TTS 合成成功（audio_speech），{len(audio_data)} 字节")
            return audio_data
        logger.warning("TTS audio_speech 返回数据过小，尝试兜底路径")
    except TTSError:
        logger.warning("TTS audio_speech 失败，尝试 chat_audio_out 兜底")

    # 路径②：chat completions + audio output 兜底
    try:
        audio_data = _synthesize_via_chat_audio_out(cleaned)
        if audio_data and len(audio_data) > 100:
            logger.info(f"TTS 合成成功（chat_audio_out），{len(audio_data)} 字节")
            return audio_data
        raise TTSError("TTS 兜底路径返回数据过小")
    except TTSError:
        raise
    except Exception as e:
        logger.error(f"TTS 兜底路径异常: {e}")
        raise TTSError(f"TTS 语音合成失败: {e}") from e
