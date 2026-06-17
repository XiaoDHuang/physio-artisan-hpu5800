"""
大模型图片生成适配器

通过 POST /images/generations 生成健康报告可视化图片。

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
    """带 429 快速重试的 requests 调用（最多重试1次，应对偶发网络抖动）。"""
    max_retries = 1
    delays = [2]
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
        "生成一张简体中文健康报告可视化信息图。",
        "【关键语言要求】所有文字必须是简体中文，严格禁止繁体字（例如：写'身体'不写'身體'，写'运动'不写'運動'，写'饮食'不写'飲食'，写'睡眠'不写'睡眠'）。",
        "",
        "【整体风格】白色底(#ffffff)，翠绿色(#3fbf8f)主色调，现代简约卡片式UI，卡片间距≥20px，每个卡片有独立圆角16px、淡灰色阴影。",
        "",
        "【顶部 — KPI 横排4卡片】等宽4列，每列一个圆角卡片，卡片内：上排小字标签(灰色)、下排大字数值(翠绿色加粗)：",
        f"  卡片1：标签「综合健康评分」 数值「{v(kpi, 'health_score')} / 100」",
        f"  卡片2：标签「身体状态」 数值「{v(kpi, 'status')}」",
        f"  卡片3：标签「运动达标率」 数值「{v(kpi, 'exercise_rate')}%」",
        f"  卡片4：标签「健康风险」 数值「{v(kpi, 'risk')}」",
        "",
        "【左栏上半部 — 身体指标概览卡片】宽约60%，标题「身体指标概览」，卡片内左右两栏：",
        "  左栏竖排3行指标（标签+数值）：",
        f"    「心率」{v(body, 'heart_rate')} 次/分",
        f"    「体重」{v(body, 'weight_kg')} kg",
        f"    「基础代谢」{v(body, 'bmr')} 千卡",
        "  右栏竖排3行指标（标签+数值）：",
        f"    「BMI」{v(body, 'bmi')}",
        f"    「体脂率」{v(body, 'body_fat_pct')}%",
        f"    「肌肉量」{v(body, 'muscle_mass_kg')} kg",
        f"  底部小字：「{v(body, 'update_date')} 更新」",
        "",
        "【左栏下半部 — 健康建议卡片】标题「健康建议」，3列横向排布，每列一个独立小卡片，卡片内有图标+标题+描述文字，文字小三号：",
        f"  列1（运动）标题「运动建议」，内容「{v(health_advice, 'exercise')}」",
        f"  列2（睡眠）标题「睡眠建议」，内容「{v(health_advice, 'sleep')}」",
        f"  列3（饮食）标题「饮食建议」，内容「{v(health_advice, 'nutrition')}」",
        "",
        "【右栏 — 睡眠/饮食/运动 3个竖向堆叠卡片】宽约35%，3个独立卡片，间距明显，每个卡片标题+数据行：",
        f"  卡片A「睡眠监测」：评分 {v(sleep, 'score')}/100  ·  总时长 {v(sleep, 'total_hours')} 小时",
        f"  卡片B「饮食监测」：摄入 {v(nutrition, 'total_calories')} 千卡  ·  均衡度 {v(nutrition, 'balance_score')}",
        f"  卡片C「运动监测」：步数 {v(exercise, 'steps')}/{v(exercise, 'steps_goal', '8000')}  ·  时长 {v(exercise, 'duration_minutes')} 分钟  ·  强度 {v(exercise, 'intensity')}  ·  消耗 {v(exercise, 'calories_burned')} 千卡",
        "",
        "【布局规范】",
        "  - 整体宽度960px，左栏60%右栏35%，中间5%留白",
        "  - KPI行高度约100px，身体指标卡片高度约200px，健康建议卡片高度约160px",
        "  - 右栏3个卡片高度均分，各约120px",
        "  - 所有文字必须使用简体中文（Simplified Chinese），禁止任何繁体字",
        "  - 数字使用粗体、翠绿色或深灰色，标签使用常规灰色",
        "  - 卡片背景#fafbfc，阴影0 2px 8px rgba(0,0,0,0.08)",
        "  - 底部一行小字：「AI健康助手 · 数据仅供参考」",
    ]
    return "\n".join(lines)


def _generate_via_image_gen(prompt: str) -> bytes:
    """POST /images/generations 图片生成。

    返回: PNG 图片字节
    """
    base_url = config.IMAGE_BASE_URL.rstrip("/")
    url = f"{base_url}/images/generations"

    payload = {
        "model": config.IMAGE_MODEL,
        "prompt": prompt,
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
            timeout=90,
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

    # 直接走 /images/generations（apiyi 网关不支持 chat completions 的 modalities: ["image"]）
    try:
        img_data = _generate_via_image_gen(prompt)
        if img_data and len(img_data) > 500:
            logger.info(f"Image Gen 生成成功（image_gen），{len(img_data)} 字节")
            return img_data
        raise ImageGenError("Image Gen 返回数据过小")
    except ImageGenError:
        raise
    except Exception as e:
        logger.error(f"Image Gen 异常: {e}")
        raise ImageGenError(f"图片生成失败: {e}") from e
