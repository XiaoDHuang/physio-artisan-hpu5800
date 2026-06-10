"""
「暴汗艺术家」数据录入层（intake）

职责（对应 /chat 多模态数据录入需求）：
- 定义三类录入数据的字段规范与必填项（运动负荷 / 饮食记录 / 身体测量）；
- 校验关键字段准确性，缺失关键字段则不入库（由 /chat 多轮追问补齐）；
- 校验通过后写入 PostgreSQL（exercise_records / nutrition_logs / users）；
- 提供多模态图识别的 mock 入口（预留真实 src/vision 接入 hook）。

数据写入对齐既有表的 JSONB 列，仅对 users 增补一个 body_fat_pct 列（幂等 DDL）。

适用于大模型技术初级用户：
- "槽位填充(slot filling)" = 多轮对话里逐步把表单字段补齐。
- "幂等 DDL" = ADD COLUMN IF NOT EXISTS，重复执行不报错、不破坏已有数据。
"""

from __future__ import annotations

import logging
from datetime import date as _date
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger("api_server")

# 暂无用户态：统一归属到 seed_xiaoming.sql 插入的演示用户（小明 id=1）
DEFAULT_USER_ID = 1


# =============================================================================
# 一、录入数据规范（字段 / 必填 / 类型 / 中文标签）
# =============================================================================
DATA_ENTRY_SCHEMAS: Dict[str, Dict[str, Any]] = {
    # 运动负荷（设计方案 §8.3 exercise_record）
    "exercise": {
        "label": "运动负荷",
        "required": ["duration_minutes", "peak_hr", "hr_60s", "rpe"],
        "types": {"duration_minutes": int, "peak_hr": int, "hr_60s": int, "rpe": int},
        "field_labels": {
            "duration_minutes": "训练时长(分钟)", "peak_hr": "峰值心率(bpm)",
            "hr_60s": "运动后60秒心率(bpm)", "rpe": "自评疲劳度RPE(1-10)",
            "exercise_type": "运动类型",
        },
    },
    # 饮食记录（设计方案 §8.4 diet_narrative）
    "nutrition": {
        "label": "饮食记录",
        "required": ["diet_narrative"],
        "types": {"diet_narrative": str},
        "field_labels": {"diet_narrative": "三餐食材与分量描述", "meal_type": "餐别"},
    },
    # 身体测量（设计方案 §8.4 user_inputs；muscle_mass_kg 为可选，支持后期对话自动录入）
    "body": {
        "label": "身体测量",
        "required": ["weight_kg", "body_fat_pct"],
        "types": {"weight_kg": float, "body_fat_pct": float, "muscle_mass_kg": float},
        "field_labels": {"weight_kg": "体重(kg)", "body_fat_pct": "体脂率(%)",
                         "muscle_mass_kg": "肌肉量(kg)"},
    },
}


def field_label(data_type: str, field: str) -> str:
    return DATA_ENTRY_SCHEMAS.get(data_type, {}).get("field_labels", {}).get(field, field)


# =============================================================================
# 二、字段校验（类型可转换 + 必填齐全）
# =============================================================================
def _coerce(value: Any, typ) -> Optional[Any]:
    """把值转成目标类型；失败返回 None。"""
    if value is None:
        return None
    try:
        if typ is str:
            s = str(value).strip()
            return s or None
        if typ is int:
            return int(float(value))
        if typ is float:
            return float(value)
    except (ValueError, TypeError):
        return None
    return value


def validate_entry(data_type: str, fields: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any]]:
    """校验某类录入数据。

    Returns:
        (missing_labels, cleaned) —— missing_labels 为缺失/非法的必填字段中文标签列表；
        cleaned 为已做类型转换的有效字段字典。
    """
    schema = DATA_ENTRY_SCHEMAS.get(data_type)
    if not schema:
        return ["未知录入类型"], {}

    cleaned: Dict[str, Any] = {}
    missing: List[str] = []
    types = schema["types"]

    # 转换所有出现的字段
    for key, typ in types.items():
        if key in fields:
            v = _coerce(fields[key], typ)
            if v is not None:
                cleaned[key] = v
    # 透传可选的非类型字段（如 exercise_type / meal_type）
    for opt in ("exercise_type", "meal_type"):
        if fields.get(opt):
            cleaned[opt] = str(fields[opt]).strip()

    # 必填检查
    for key in schema["required"]:
        if key not in cleaned:
            missing.append(field_label(data_type, key))

    return missing, cleaned


# =============================================================================
# 三、数据库写入（幂等 DDL + 入库）
# =============================================================================
_DDL_DONE = False


def _ensure_schema(conn) -> None:
    """幂等补齐演示所需的列/索引（首次写入时执行一次）。"""
    with conn.cursor() as cur:
        # users 增补体脂率/肌肉量列（设计方案与仪表盘需要，库内原缺）
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS body_fat_pct FLOAT")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS muscle_mass_kg FLOAT")
        # ai_conversations 以 session_id 作为会话键，需唯一索引以支持 UPSERT
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_ai_conv_session "
            "ON ai_conversations(session_id)"
        )


def _run(fn):
    """从连接池借连接执行 fn(conn)，自动提交/回滚/归还。"""
    from store.db import get_pool
    global _DDL_DONE
    pool = get_pool()
    conn = pool.getconn()
    try:
        if not _DDL_DONE:
            _ensure_schema(conn)
            _DDL_DONE = True
        result = fn(conn)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def save_entry(data_type: str, cleaned: Dict[str, Any],
               user_id: int = DEFAULT_USER_ID, on_date: Optional[str] = None) -> Dict[str, Any]:
    """把校验通过的录入数据写入对应表。

    - exercise -> exercise_records.analysis_result(JSONB)
    - nutrition -> nutrition_logs.nutrition_result(JSONB)
    - body     -> users 行更新(weight_kg, body_fat_pct)

    Returns: {"saved": True, "table": ..., "record": {...}}
    """
    from psycopg2.extras import Json
    the_date = on_date or _date.today().isoformat()

    if data_type == "exercise":
        payload = {k: cleaned[k] for k in ("duration_minutes", "peak_hr", "hr_60s", "rpe") if k in cleaned}

        def _ins(conn):
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO exercise_records (user_id, date, exercise_type, analysis_result) "
                    "VALUES (%s, %s, %s, %s) RETURNING id",
                    (user_id, the_date, cleaned.get("exercise_type", "用户录入"), Json(payload)),
                )
                return cur.fetchone()[0]

        rid = _run(_ins)
        return {"saved": True, "table": "exercise_records", "record_id": rid, "record": payload}

    if data_type == "nutrition":
        payload = {"diet_narrative": cleaned["diet_narrative"]}

        def _ins(conn):
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO nutrition_logs (user_id, date, meal_type, nutrition_result) "
                    "VALUES (%s, %s, %s, %s) RETURNING id",
                    (user_id, the_date, cleaned.get("meal_type", "daily"), Json(payload)),
                )
                return cur.fetchone()[0]

        rid = _run(_ins)
        return {"saved": True, "table": "nutrition_logs", "record_id": rid, "record": payload}

    if data_type == "body":
        muscle = cleaned.get("muscle_mass_kg")

        def _upd(conn):
            with conn.cursor() as cur:
                if muscle is not None:
                    cur.execute(
                        "UPDATE users SET weight_kg = %s, body_fat_pct = %s, muscle_mass_kg = %s, "
                        "updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                        (cleaned["weight_kg"], cleaned["body_fat_pct"], muscle, user_id),
                    )
                else:
                    cur.execute(
                        "UPDATE users SET weight_kg = %s, body_fat_pct = %s, "
                        "updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                        (cleaned["weight_kg"], cleaned["body_fat_pct"], user_id),
                    )
                return cur.rowcount

        n = _run(_upd)
        rec = {"weight_kg": cleaned["weight_kg"], "body_fat_pct": cleaned["body_fat_pct"]}
        if muscle is not None:
            rec["muscle_mass_kg"] = muscle
        return {"saved": True, "table": "users", "updated_rows": n, "record": rec}

    return {"saved": False, "error": f"未知录入类型: {data_type}"}


# =============================================================================
# 四、多模态图识别（mock + 真实 hook）
# =============================================================================
def recognize_image(image_b64: Optional[str], data_type: Optional[str]) -> Dict[str, Any]:
    """从上传图片中识别录入字段。

    本期为 mock：返回带 [图识别] 标记的占位字段；
    预留真实接入 hook —— 后续可改为调用 src/vision/food_analyzer 等。

    Args:
        image_b64: 图片的 base64（或路径），本期不真正解码。
        data_type: 期望的数据类型，影响返回字段。
    """
    if not image_b64:
        return {}

    # TODO(后续): 接入真实视觉模型
    #   from src.vision.food_analyzer import analyze_food
    #   return analyze_food(image_b64)  # -> {"diet_narrative": ...}
    if data_type == "nutrition":
        return {"diet_narrative": "[图识别·mock] 一份煎三文鱼配藜麦沙拉，约150g"}
    if data_type == "body":
        return {"weight_kg": 79.5, "body_fat_pct": 23.5, "_note": "[图识别·mock] 体脂秤读数"}
    if data_type == "exercise":
        return {"_note": "[图识别·mock] 运动截图，建议同时补充心率/RPE"}
    # 类型未知时给一个食物默认（最常见的拍照场景）
    return {"diet_narrative": "[图识别·mock] 餐盘图片", "_note": "未指定类型，按饮食处理"}
