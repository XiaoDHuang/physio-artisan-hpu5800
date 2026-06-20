"""
千问 ASR 语音转文字适配器

封装 ASR 调用，支持两种路径（由 ASR_MODE 配置切换）：
- transcriptions: POST /audio/transcriptions（OpenAI 音频接口，Whisper 风格）
- chat_audio: POST /chat/completions（多模态 input_audio base64，当前网关首选）

经 spike 验证：apiyi 网关仅支持 chat_audio 路径（/audio/transcriptions 返回 404），
默认使用 qwen3-omni-flash 模型。
"""

import base64
import logging
import time
from typing import Dict, Optional

import requests

from config.langgraph_config import langgraph_config as config

logger = logging.getLogger("asr")
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


class ASRError(Exception):
    """ASR 受控异常，路由层捕获后转 5xx。"""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


class ASRValidationError(Exception):
    """ASR 参数校验异常，路由层捕获后转 4xx。"""

    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


def _post_with_retry(method, url, **kwargs):
    """带 429 指数退避的 requests 调用。

    短时间内高频 ASR 会触发 apiyi 网关限流（HTTP 429），
    用 Fibonacci 数列退避再试 3 次，同时拉长 timeout 兜底。
    """
    max_retries = 3
    delays = [1, 2, 3]  # Fibonacci: 1s, 2s, 3s
    for attempt in range(max_retries + 1):
        try:
            resp = requests.request(method, url, **kwargs)
            if resp.status_code == 429 and attempt < max_retries:
                delay = delays[attempt]
                logger.warning(f"ASR 被限流(429)，{delay}s 后重试({attempt + 1}/{max_retries})")
                time.sleep(delay)
                continue
            return resp
        except requests.RequestException:
            if attempt < max_retries:
                delay = delays[attempt]
                logger.warning(f"ASR 请求失败，{delay}s 后重试({attempt + 1}/{max_retries})")
                time.sleep(delay)
                continue
            raise
    # 理论上不会到这里，但 LSP 安心
    raise ASRError("ASR 服务不可用（多次重试后仍失败）")


def _estimate_duration_ms(data: bytes, mime: str) -> Optional[int]:
    """估算音频时长（毫秒），仅做尽力而为的近似。

    浏览器 MediaRecorder 产出的 webm 容器头含 Segment/Info/TimecodeScale
    和 Block 时间戳，这里用简易启发式按文件大小 ÷ 码率近似：
      - webm/opus: 假设约 32 kbps（4 KB/s），实际码率因编码器而异，偏保守。
      - wav: 假设 16-bit 16kHz mono PCM（32 KB/s），未经压缩的线性码流。
      - mp4/m4a aac: 假设约 32 kbps（4 KB/s），与 webm 相近。
    若无法根据 mime 推断码率，返回 None（调用方应走 no-estimate 分支，
    不因无法估算而拒绝请求）。
    """
    if not data:
        return None
    # webm/opus ~32kbps (4KB/s) —— 粗略估算，实际码率可能 ±30%
    if "webm" in mime or "opus" in mime:
        return max(0, int(len(data) / 4000 * 1000))
    # wav: 16-bit 16kHz mono PCM → 32KB/s，无压缩，估算较准
    if "wav" in mime:
        return max(0, int(len(data) / 32000 * 1000))
    # m4a/mp4 aac ~32kbps —— 粗略估算，同 webm
    if "mp4" in mime or "aac" in mime or "m4a" in mime:
        return max(0, int(len(data) / 4000 * 1000))
    return None


def _transcribe_via_transcriptions(data: bytes, mime: str, filename: str) -> Dict:
    """路径①：OpenAI 音频转录接口。

    POST {base_url}/audio/transcriptions
    multipart: file=(filename, data, mime) + model=ASR_MODEL
    """
    base_url = config.ASR_BASE_URL.rstrip("/")
    url = f"{base_url}/audio/transcriptions"

    try:
        resp = _post_with_retry("POST", url,
            files={"file": (filename, data, mime)},
            data={"model": config.ASR_MODEL},
            headers={"Authorization": f"Bearer {config.ASR_API_KEY}"},
            timeout=120,
        )
    except requests.RequestException as e:
        logger.error(f"ASR transcriptions 请求失败: {e}")
        raise ASRError(f"ASR 服务请求失败: {e}") from e

    if not resp.ok:
        logger.error(f"ASR transcriptions 上游错误 {resp.status_code}: {resp.text[:300]}")
        raise ASRError(f"ASR 转录服务返回 {resp.status_code}")

    try:
        body = resp.json()
    except ValueError:
        logger.error(f"ASR transcriptions 非 JSON 响应: {resp.text[:200]}")
        raise ASRError("ASR 转录服务返回非 JSON 响应")

    text = (body.get("text") or "").strip()
    duration_ms = body.get("duration")  # OpenAI 返回秒数（浮点）
    if duration_ms is not None:
        duration_ms = int(float(duration_ms) * 1000)

    return {"text": text, "duration_ms": duration_ms, "model": config.ASR_MODEL}


def _transcribe_via_chat_audio(data: bytes, mime: str, filename: str) -> Dict:
    """路径②：多模态 chat completions + input_audio(base64)。

    将音频编码为 base64 data URI，作为 input_audio 内容块发送。
    当前 apiyi 网关经 spike 验证可用（qwen3-omni-flash）。
    """
    base_url = config.ASR_BASE_URL.rstrip("/")
    url = f"{base_url}/chat/completions"

    b64 = base64.b64encode(data).decode("ascii")
    # 格式弦：取 mime 或从 filename 推断
    fmt = "wav"
    if "webm" in mime:
        fmt = "webm"
    elif "mp4" in mime or "m4a" in mime:
        fmt = "mp4"
    elif "aac" in mime:
        fmt = "aac"
    elif "mp3" in mime or "mpeg" in mime:
        fmt = "mp3"

    data_uri = f"data:audio/{fmt};base64,{b64}"

    payload = {
        "model": config.ASR_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "请逐字转写这段音频中的语音内容。"
                            "只输出转写后的纯文本，不要添加任何解释、标点说明或其他内容。"
                            "如果音频中没有可辨识的语音，输出空字符串。"
                        ),
                    },
                    {
                        "type": "input_audio",
                        "input_audio": {"data": data_uri, "format": fmt},
                    },
                ],
            }
        ],
        "max_tokens": 1024,
        "temperature": 0,
    }

    try:
        resp = _post_with_retry("POST", url,
            json=payload,
            headers={
                "Authorization": f"Bearer {config.ASR_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=120,  # base64 WAV 上传 + 网关处理，给足余量
        )
    except requests.RequestException as e:
        logger.error(f"ASR chat_audio 请求失败: {e}")
        raise ASRError(f"ASR 服务请求失败: {e}") from e

    if not resp.ok:
        logger.error(f"ASR chat_audio 上游错误 {resp.status_code}: {resp.text[:300]}")
        raise ASRError(f"ASR 语音识别服务返回 {resp.status_code}")

    try:
        body = resp.json()
    except ValueError:
        logger.error(f"ASR chat_audio 非 JSON 响应: {resp.text[:200]}")
        raise ASRError("ASR 语音识别服务返回非 JSON 响应")

    text = ""
    try:
        msg = body["choices"][0]["message"]
        c = msg.get("content")
        # 归一化：部分模型/网关可能返回 list[part] 而非纯 str
        if isinstance(c, list):
            c = "".join(
                p.get("text", "") for p in c
                if isinstance(p, dict) and p.get("type") == "text"
            )
        text = (c or "").strip()
    except (KeyError, IndexError, TypeError):
        logger.error(f"ASR chat_audio 响应结构异常: {body}")

    # 估算时长
    duration_ms = _estimate_duration_ms(data, mime)

    return {"text": text, "duration_ms": duration_ms, "model": config.ASR_MODEL}


def transcribe_audio(data: bytes, mime: str, filename: str) -> Dict:
    """语音转文字主入口。

    参数：
        data: 音频原始字节
        mime: MIME 类型（如 "audio/webm;codecs=opus"）
        filename: 原始文件名（如 "recording.webm"）

    返回：
        {"text": str, "duration_ms": int|None, "model": str}

    异常：
        ASRError — 上游 ASR 调用失败
        ASRValidationError — 参数校验失败
    """
    if not data:
        raise ASRValidationError("音频数据为空")

    # 时长上限校验（尽力估算；无法估算时不误拦）
    est_ms = _estimate_duration_ms(data, mime)
    max_ms = config.ASR_MAX_SECONDS * 1000
    if est_ms is not None and est_ms > max_ms:
        raise ASRValidationError(
            f"音频过长（最长 {config.ASR_MAX_SECONDS}s），"
            f"估算约 {est_ms / 1000:.0f}s"
        )

    mode = config.ASR_MODE.strip().lower()

    if mode == "transcriptions":
        return _transcribe_via_transcriptions(data, mime, filename)
    elif mode == "chat_audio":
        return _transcribe_via_chat_audio(data, mime, filename)
    else:
        logger.error(f"未知的 ASR_MODE: {mode}")
        raise ASRError(f"不支持的 ASR_MODE: {mode}")
