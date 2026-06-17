"""
大模型图片生成适配器

支持两种路径：
- chat_image: POST /chat/completions + modalities: ["image"]（主路径）
- image_gen: POST /images/generations（兜底）

对称于 ASR / TTS，形成完整的多模态三角。
"""
import json
import logging
import time
from typing import Optional

import requests

from config.langgraph_config import langgraph_config as config

logger = logging.getLogger("image_gen")
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


class ImageGenError(Exception):
    """图片生成受控异常。"""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


class ImageGenValidationError(Exception):
    """参数校验异常。"""

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
                logger.warning(f"Image Gen 被限流(429)，{delay}s 后重试({attempt + 1}/{max_retries})")
                time.sleep(delay)
                continue
            return resp
        except requests.RequestException:
            if attempt < max_retries:
                delay = delays[attempt]
                logger.warning(f"Image Gen 请求失败，{delay}s 后重试({attempt + 1}/{max_retries})")
                time.sleep(delay)
                continue
            raise
    raise ImageGenError("图片生成服务不可用（多次重试后仍失败）")


def build_report_prompt(data: dict) -> str:
    """根据报告 JSON 数据构造中文图片生成提示词。

    要求：设计风格、布局结构、数据完整性、中文清晰标注。
    """
    kpi = data.get("kpi", {})
    body = data.get("body", {})
    sleep = data.get("sleep", {})
    nutrition = data.get("nutrition", {})
    exercise = data.get("exercise", {})
    health_advice = data.get("healthAdvice", {})

    def v(d, key, default="—"):
        val = d.get(key)
        return str(val) if val is not None and val != "" else default

    lines = [
        "生成一张中文健康报告可视化信息图，风格简洁专业，白底，卡片式布局，配色以翠绿色(#3fbf8f)为主色调。",
        "",
        "=== 顶部 KPI 区域（4 列横向排布）===",
        f"综合健康评分：{v(kpi, 'health_score')} / 100     身体状态：{v(kpi, 'status')}",
        f"运动达标率：{v(kpi, 'exercise_rate')}%           健康风险：{v(kpi, 'risk')}",
        "",
        "=== 身体指标概览（居中人体剪影，左右各三行数据）===",
        f"心率：{v(body, 'heart_rate')} 次/分     BMI：{v(body, 'bmi')}     体脂率：{v(body, 'body_fat_pct')}%",
        f"体重：{v(body, 'weight_kg')} kg       基础代谢：{v(body, 'bmr')} 千卡     肌肉量：{v(body, 'muscle_mass_kg')} kg",
        f"数据来源：{v(body, 'update_date')}",
        "",
        "=== 健康建议（三列卡片：运动/睡眠/饮食）===",
        f"运动建议：{v(health_advice, 'exercise')}",
        f"睡眠建议：{v(health_advice, 'sleep')}",
        f"饮食建议：{v(health_advice, 'nutrition')}",
        "",
        "=== 右侧边栏 ===",
        f"睡眠评分：{v(sleep, 'score')} / 100   总睡眠：{v(sleep, 'total_hours')} 小时",
        f"饮食摄入：{v(nutrition, 'total_calories')} 千卡   均衡度：{v(nutrition, 'balance_score')}",
        f"今日步数：{v(exercise, 'steps')} / {v(exercise, 'steps_goal', '8000')} 步   运动时长：{v(exercise, 'duration_minutes')} 分钟",
        f"运动强度：{v(exercise, 'intensity')}   消耗热量：{v(exercise, 'calories_burned')} 千卡",
        "",
        "=== 布局要求 ===",
        "整体信息图格式，自上而下排布：KPI行 → 身体概览+健康建议(左栏宽) + 睡眠/饮食/运动(右栏窄) → 底部签章行",
        "所有中文必须使用简体中文（简体字），禁止使用繁体字",
        "所有中文使用清晰衬线字体或宋体，数字用等宽数字字体",
        "卡片圆角16px，带淡阴影，数据用大号加粗字体显示",
        "底部标注：AI健康助手 · 数据仅供参考 · 生成日期：今日",
    ]
    return "\n".join(lines)


def _generate_via_chat_image(data: dict, prompt: str) -> bytes:
    """路径①：Chat Completions + modalities: ["image"]。

    返回: PNG 图片字节
    """
    base_url = config.IMAGE_BASE_URL.rstrip("/")
    url = f"{base_url}/chat/completions"

    payload = {
        "model": config.IMAGE_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "modalities": ["image"],
        "image": {
            "size": config.IMAGE_SIZE,
            "quality": "standard",
        },
        "max_tokens": 2048,
    }

    try:
        resp = _post_with_retry("POST", url,
            json=payload,
            headers={
                "Authorization": f"Bearer {config.IMAGE_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=120,
        )
    except requests.RequestException as e:
        logger.error(f"Image Gen chat_image 请求失败: {e}")
        raise ImageGenError(f"图片生成服务请求失败: {e}") from e

    if not resp.ok:
        logger.error(f"Image Gen chat_image 上游错误 {resp.status_code}: {resp.text[:300]}")
        raise ImageGenError(f"图片生成服务返回 {resp.status_code}")

    # 从 chat completions 响应中提取 image data
    try:
        body = resp.json()
        # 尝试多种响应格式
        output = body["choices"][0]["message"]
        # 格式1: modalities 返回的 image content
        if isinstance(output.get("content"), list):
            for part in output["content"]:
                if isinstance(part, dict) and part.get("type") == "image":
                    img_data = part.get("image_url", {}).get("url", "") or part.get("data", "")
                    if img_data:
                        import base64
                        if img_data.startswith("data:image"):
                            img_data = img_data.split(",", 1)[1]
                        return base64.b64decode(img_data)
        # 格式2: message.image.data
        img = output.get("image", {})
        img_data = img.get("data", "") or img.get("url", "")
        if img_data:
            import base64
            if img_data.startswith("data:image"):
                img_data = img_data.split(",", 1)[1]
            return base64.b64decode(img_data)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Image Gen chat_image 解析失败: {e}")
        raise ImageGenError("图片生成响应解析失败：未找到图片数据")

    raise ImageGenError("图片生成响应解析失败：未找到图片数据")


def _generate_via_image_gen(prompt: str) -> bytes:
    """路径②：POST /images/generations 标准端点兜底。

    返回: PNG 图片字节
    """
    base_url = config.IMAGE_BASE_URL.rstrip("/")
    url = f"{base_url}/images/generations"

    # 用简洁 prompt（取前 1000 字符）
    short_prompt = prompt[:1000]

    payload = {
        "model": config.IMAGE_MODEL,
        "prompt": short_prompt,
        "n": 1,
        "size": config.IMAGE_SIZE,
        "response_format": "b64_json",
    }

    try:
        resp = _post_with_retry("POST", url,
            json=payload,
            headers={
                "Authorization": f"Bearer {config.IMAGE_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=120,
        )
    except requests.RequestException as e:
        logger.error(f"Image Gen image_gen 请求失败: {e}")
        raise ImageGenError(f"图片生成服务请求失败: {e}") from e

    if not resp.ok:
        logger.error(f"Image Gen image_gen 上游错误 {resp.status_code}: {resp.text[:300]}")
        raise ImageGenError(f"图片生成服务返回 {resp.status_code}")

    try:
        body = resp.json()
        b64 = body["data"][0].get("b64_json", "") or body["data"][0].get("url", "")
        if b64:
            import base64
            return base64.b64decode(b64)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Image Gen image_gen 解析失败: {e}")

    # 尝试 url 下载
    try:
        img_url = resp.json()["data"][0].get("url", "")
        if img_url:
            img_resp = requests.get(img_url, timeout=30)
            if img_resp.ok:
                return img_resp.content
    except Exception:
        pass

    raise ImageGenError("图片生成响应解析失败：未找到图片数据")


def generate_report_image(data: dict) -> bytes:
    """图片生成主入口。

    参数：
        data: 报告页面数据字典

    返回：
        PNG 图片字节

    异常：
        ImageGenError — 上游调用失败
        ImageGenValidationError — 参数校验失败
    """
    if not data or not isinstance(data, dict):
        raise ImageGenValidationError("报告数据为空或格式错误")

    prompt = build_report_prompt(data)
    logger.info(f"Image Gen prompt 长度: {len(prompt)} 字符")

    # 路径①：Chat Completions + modalities: ["image"]（主路径）
    try:
        img_data = _generate_via_chat_image(data, prompt)
        if img_data and len(img_data) > 500:
            logger.info(f"Image Gen 生成成功（chat_image），{len(img_data)} 字节")
            return img_data
        logger.warning("Image Gen chat_image 返回数据过小，尝试兜底路径")
    except ImageGenError:
        logger.warning("Image Gen chat_image 失败，尝试 image_gen 兜底")

    # 路径②：/images/generations 兜底
    try:
        img_data = _generate_via_image_gen(prompt)
        if img_data and len(img_data) > 500:
            logger.info(f"Image Gen 生成成功（image_gen），{len(img_data)} 字节")
            return img_data
        raise ImageGenError("Image Gen 兜底路径返回数据过小")
    except ImageGenError:
        raise
    except Exception as e:
        logger.error(f"Image Gen 兜底路径异常: {e}")
        raise ImageGenError(f"图片生成失败: {e}") from e
