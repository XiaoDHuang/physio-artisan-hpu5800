#!/usr/bin/env python3
"""
「暴汗艺术家」健康决策助手 - FastAPI 后端服务

接口总览：
- POST /chat               任务型对话中枢（意图路由 + 数据录入 + 报告触发），返回结构化 JSON
- POST /plan               一键触发多智能体健康决策（异步后台任务），返回 task_id
- GET  /status/{task_id}   查询任务/报告状态
- GET  /conversations      会话列表（存于 ai_conversations）
- GET  /conversations/{id} 会话历史
- DELETE /conversations/{id} 清空会话
- GET  /health, GET /      健康检查 / 服务信息

/chat 仅服务两类任务（设计方案）：
1) 报告生成：识别到"生成报告/体检/分析"诉求 -> 启动 run_health_assessment 工作流
2) 数据录入：运动负荷 / 饮食记录 / 身体测量（含多模态图识别）-> 校验关键字段，
   缺失则多轮追问且不入库，齐全才写库
3) 偏题：礼貌拒答并引导回上述两类任务，不提供其他闲聊能力
"""

import sys
import os
import json
import uuid
import asyncio
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.langgraph_config import langgraph_config as config
from store import get_store
from store.postgres_store import save_assessment_artifacts, save_user_plan
from agents.langgraph_agents import LangGraphHealthAgents
from agents import intake
from agents import health_data as hdata
from agents.safety import screen_text
from agents.asr import transcribe_audio, ASRError, ASRValidationError
from agents.tts import synthesize_speech, TTSError, TTSValidationError
from agents.image_gen import generate_report_image, ImageGenError, ImageGenValidationError
from agents.copy.report_replies import (
    immediate_reply,
    progress_message,
    MSG_TASK_STARTED,
    MSG_TASK_COMPLETED,
    MSG_TASK_FAILED,
)
from store.safety_store import save_safety_log
from store.postgres_store import load_latest_assessment


# --------------------------- 日志配置 ---------------------------
def setup_api_logger() -> logging.Logger:
    logger = logging.getLogger("api_server")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        fh = logging.FileHandler("logs/backend.log", encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(fh)
    return logger


api_logger = setup_api_logger()

# --------------------------- 应用初始化 ---------------------------
app = FastAPI(
    title="暴汗艺术家 - 健康决策助手 API",
    description="🤖 基于 LangGraph 多智能体的闭环健康决策系统",
    version="3.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 任务状态（内存）：task_id -> {status, progress, result, ...}，供 /status 轮询
assessment_tasks: Dict[str, Dict[str, Any]] = {}

# 多智能体系统单例（图编译一次复用）
_agents_singleton: Optional[LangGraphHealthAgents] = None


def get_agents() -> LangGraphHealthAgents:
    global _agents_singleton
    if _agents_singleton is None:
        _agents_singleton = LangGraphHealthAgents()
    return _agents_singleton


# --------------------------- 数据模型 ---------------------------
class ChatRequest(BaseModel):
    message: str = Field(..., description="用户本次消息", examples=["帮我生成今天的健康体检报告"])
    conversation_id: Optional[str] = Field(default=None, description="会话ID，为空表示新建会话")
    image_base64: Optional[str] = Field(default=None, description="可选：上传图片(base64/路径)用于多模态识别录入")
    mode: Optional[str] = Field(default=None, description="可选：报告场景 control|experiment")
    user_id: int = Field(default=intake.DEFAULT_USER_ID, description="用户 ID，默认演示用户")
    date: Optional[str] = Field(default=None, description="报告锚点日 YYYY-MM-DD，默认今天")


class SleepEntryRequest(BaseModel):
    bedtime: str = Field(..., description="入睡时间 ISO 格式，如 2026-06-01T23:20")
    wake_time: str = Field(..., description="起床时间 ISO 格式，如 2026-06-02T07:20")
    nap_minutes: Optional[int] = Field(default=None, description="小憩分钟数（可选）")
    on_date: Optional[str] = Field(default=None, description="日期 YYYY-MM-DD，默认今天")
    user_id: int = Field(default=1, description="用户 ID")


class SleepEntryResponse(BaseModel):
    saved: bool
    sleep_data: Dict[str, Any]


class SleepOverviewResponse(BaseModel):
    user_id: int
    sleep: Dict[str, Any]
    sources: Dict[str, str]


class ExerciseOverviewResponse(BaseModel):
    user_id: int
    exercise: Dict[str, Any]
    sources: Dict[str, str]


class NutritionOverviewResponse(BaseModel):
    user_id: int
    date: str
    nutrition: Dict[str, Any]
    sources: Dict[str, str]


class ChatResponse(BaseModel):
    conversation_id: str
    intent: str = Field(..., description="report | data_entry | other")
    data_type: Optional[str] = Field(None, description="exercise | nutrition | body | null")
    reply: str = Field(..., description="面向用户的话术")
    extracted: Dict[str, Any] = Field(default_factory=dict, description="已提取/识别的字段")
    missing: List[str] = Field(default_factory=list, description="仍缺失的关键字段(中文标签)")
    can_proceed: bool = Field(False, description="数据是否齐全可入库/可继续")
    saved: bool = Field(False, description="本轮是否已入库")
    task_id: Optional[str] = Field(None, description="报告任务ID(report 意图时返回)")
    anchor_date: Optional[str] = Field(None, description="报告锚点日(report 意图时回显)")


class PlanRequest(BaseModel):
    user_id: int = Field(default=intake.DEFAULT_USER_ID, description="用户ID，默认演示用户(小明 id=1)")
    mode: str = Field(default="control", description="场景：control(放任恶化) | experiment(积极恢复)")
    conversation_id: Optional[str] = Field(default=None, description="可选：关联的会话ID")
    date: Optional[str] = Field(default=None, description="报告锚点日 YYYY-MM-DD，默认今天")


class PlanResponse(BaseModel):
    task_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    message: str
    result: Optional[Dict[str, Any]] = None


# --------------------------- 工具：JSON 解析 ---------------------------
def _parse_json(content: str) -> Dict[str, Any]:
    if not content:
        return {}
    text = content.strip()
    if "```" in text:
        for p in text.split("```"):
            p = p.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                text = p
                break
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e != -1 and e > s:
        text = text[s:e + 1]
    try:
        return json.loads(text)
    except Exception:  # noqa: BLE001
        return {}


# --------------------------- 意图路由 / 槽位抽取 ---------------------------
ROUTER_SYSTEM_PROMPT = """你是「暴汗艺术家」健康助手的意图理解模块。本助手只服务两类任务，严禁进行无关闲聊。

【两类任务】
1. report —— 用户想要"生成/查看健康体检报告、做身体分析、出今日训练与膳食方案"。
2. data_entry —— 用户想录入健康数据，分三种 data_type：
   - exercise(运动负荷)：训练时长(分钟)、峰值心率、运动后60秒心率、自评RPE
   - nutrition(饮食记录)：三餐食材与分量描述(diet_narrative)
   - body(身体测量)：体重(kg)、体脂率(%)
其它任何与上述无关的请求，intent 一律为 other，并礼貌引导用户回到"报告生成"或"数据录入"。

【累计抽取】请结合完整对话历史，把用户到目前为止提供的所有字段累计提取出来(多轮补充)。
数值字段只输出数字，不要带单位。

【输出】只输出严格 JSON，不要任何多余文字：
{
  "intent": "report | data_entry | other",
  "data_type": "exercise | nutrition | body | null",
  "extracted": { "字段名": 值, ... },
  "on_date": "YYYY-MM-DD | null",
  "mode": "control | experiment | null",
  "reply": "面向用户的简短中文话术"
}

字段名规范：duration_minutes, peak_hr, hr_60s, rpe, diet_narrative, weight_kg, body_fat_pct。
若用户提到报告日期（如「6月10日」「上周一」），解析为 on_date；仅年份缺省时用当前年。"""


def _route_intent(history: List[Dict[str, str]], message: str) -> Dict[str, Any]:
    """调用 LLM 做意图分类 + 累计槽位抽取。失败时回退 other。"""
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(
        model=config.OPENAI_MODEL, api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_BASE_URL, temperature=0.2,
    )
    today = date.today().isoformat()
    messages = [{"role": "system", "content": ROUTER_SYSTEM_PROMPT}, *history,
                {"role": "user", "content": f"{message}\n\n(今天是 {today})"}]
    try:
        resp = llm.invoke(messages)
        parsed = _parse_json(resp.content)
    except Exception as e:  # noqa: BLE001
        api_logger.error(f"意图路由失败: {e}")
        parsed = {}
    if not parsed:
        return {"intent": "other", "data_type": None, "extracted": {},
                "mode": None, "reply": "我可以帮你【生成健康报告】或【录入运动/饮食/身体数据】，请问需要哪一项？"}
    return parsed


def _resolve_anchor_date(explicit: Optional[str], routed_on_date: Optional[str]) -> str:
    """合并请求 date 与路由抽取 on_date，校验格式与未来日。"""
    raw = (explicit or routed_on_date or "").strip() or None
    if not raw:
        return date.today().isoformat()
    try:
        d = date.fromisoformat(raw)
    except ValueError as e:
        raise HTTPException(status_code=422, detail="date 格式须为 YYYY-MM-DD") from e
    if d > date.today():
        raise HTTPException(status_code=422, detail="不能生成未来日期的报告")
    return d.isoformat()


# --------------------------- 后台任务：运行健康决策工作流 ---------------------------
async def run_assessment_task(task_id: str, user_id: int, mode: str, session_id: str,
                              anchor_date: str):
    try:
        assessment_tasks[task_id].update(
            status="processing", progress=20,
            message=progress_message("processing", 20),
        )
        result = await asyncio.to_thread(
            lambda: get_agents().run_health_assessment(
                {"user_id": user_id, "mode": mode, "session_id": session_id,
                 "on_date": anchor_date, "anchor_date": anchor_date})
        )
        if result.get("success"):
            assessment_tasks[task_id].update(
                status="completed", progress=100,
                message=MSG_TASK_COMPLETED, result=result,
            )
            try:
                await save_assessment_artifacts(session_id, user_id, result)
            except Exception as e:  # noqa: BLE001
                api_logger.error(f"任务 {task_id} 产出回写失败: {e}")
            try:
                await save_user_plan(user_id, anchor_date, result)
            except Exception as e:  # noqa: BLE001
                api_logger.error(f"任务 {task_id} user_plans 回写失败: {e}")
        else:
            api_logger.error(f"任务 {task_id} 工作流失败: {result.get('error')}")
            assessment_tasks[task_id].update(
                status="failed", progress=100,
                message=MSG_TASK_FAILED, result=result,
            )
    except Exception as e:  # noqa: BLE001
        api_logger.error(f"任务 {task_id} 执行异常: {e}")
        assessment_tasks[task_id].update(
            status="failed", progress=100, message=MSG_TASK_FAILED,
        )


def _create_assessment_task(user_id: int, mode: str, session_id: str, anchor_date: str,
                            background_tasks: BackgroundTasks) -> str:
    task_id = str(uuid.uuid4())
    assessment_tasks[task_id] = {
        "task_id": task_id, "status": "started", "progress": 0,
        "message": MSG_TASK_STARTED, "result": None,
        "created_at": datetime.now().isoformat(),
        "user_id": user_id, "mode": mode, "session_id": session_id,
        "anchor_date": anchor_date,
    }
    background_tasks.add_task(run_assessment_task, task_id, user_id, mode, session_id, anchor_date)
    return task_id


# --------------------------- /chat ---------------------------
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """任务型对话中枢：意图路由 -> 报告触发 / 数据录入 / 引导。"""
    conversation_id = request.conversation_id or uuid.uuid4().hex
    store = get_store()
    api_logger.info(f"[/chat 会话 {conversation_id}] {request.message}")

    history = await store.get_history(conversation_id)

    # ---------- 安全输入预检（设计 §7 砸场子）：命中红线立即熔断，不路由/不入库/不生成报告 ----------
    screen = screen_text(request.message)
    if screen["blocked"]:
        block_reply = screen["block_message"]
        try:
            await save_safety_log(request.message, screen["category"], screen["level"],
                                  screen["violations"], screen["warnings"], True,
                                  request.user_id)
        except Exception as e:  # noqa: BLE001
            api_logger.error(f"安全日志写入失败: {e}")
        await store.append(conversation_id, [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": block_reply},
        ], user_id=request.user_id)
        api_logger.warning(f"[/chat 会话 {conversation_id}] 安全熔断: {screen['category']} {screen['violations']}")
        return ChatResponse(conversation_id=conversation_id, intent="blocked",
                            data_type=None, reply=block_reply, can_proceed=False)

    # 多模态：先做图识别(mock)，得到的字段并入抽取结果（文本/LLM 优先覆盖）
    image_fields = intake.recognize_image(request.image_base64, None)

    routed = _route_intent(history, request.message)
    intent = routed.get("intent", "other")
    data_type = routed.get("data_type")
    extracted = {**image_fields, **(routed.get("extracted") or {})}
    extracted.pop("_note", None)
    reply = (routed.get("reply") or "").strip()

    resp = ChatResponse(conversation_id=conversation_id, intent=intent,
                        data_type=data_type, reply=reply, extracted=extracted)

    # ---------- 报告生成 ----------
    if intent == "report":
        mode = request.mode or routed.get("mode") or "control"
        anchor_date = _resolve_anchor_date(request.date, routed.get("on_date"))
        task_id = _create_assessment_task(
            request.user_id, mode, conversation_id, anchor_date, background_tasks)
        resp.task_id = task_id
        resp.anchor_date = anchor_date
        resp.can_proceed = True
        resp.reply = immediate_reply(anchor_date, reply or None)

    # ---------- 数据录入 ----------
    elif intent == "data_entry" and data_type in intake.DATA_ENTRY_SCHEMAS:
        missing, cleaned = intake.validate_entry(data_type, extracted)
        resp.data_type = data_type
        resp.extracted = cleaned or extracted
        label = intake.DATA_ENTRY_SCHEMAS[data_type]["label"]
        if missing:
            resp.missing = missing
            resp.can_proceed = False
            resp.reply = (reply or f"正在录入【{label}】。") + \
                f"\n\n还需要你补充：{('、'.join(missing))}。补齐后我才会入库。"
        else:
            try:
                saved = await asyncio.to_thread(
                    intake.save_entry, data_type, cleaned, request.user_id)
                resp.saved = bool(saved.get("saved"))
                resp.can_proceed = True
                resp.reply = f"✅ 已记录【{label}】：{json.dumps(saved.get('record', {}), ensure_ascii=False)}。" + \
                    "你可以继续录入，或对我说\"生成报告\"。"
            except Exception as e:  # noqa: BLE001
                api_logger.error(f"录入入库失败: {e}")
                resp.reply = f"抱歉，【{label}】入库时出错了：{e}"

    # ---------- 偏题引导 ----------
    else:
        resp.intent = "other"
        resp.reply = reply or ("我是「暴汗艺术家」健康助手，只能帮你【生成健康报告】或"
                               "【录入运动负荷/饮食记录/身体测量】。请问需要哪一项？")

    # 持久化本轮对话
    await store.append(conversation_id, [
        {"role": "user", "content": request.message},
        {"role": "assistant", "content": resp.reply},
    ], user_id=request.user_id)
    return resp


# --------------------------- /plan ---------------------------
@app.post("/plan", response_model=PlanResponse)
async def create_plan(request: PlanRequest, background_tasks: BackgroundTasks):
    """一键生成健康决策报告（异步）。前端"一键生成"按钮直接调用本接口。"""
    if request.mode not in ("control", "experiment"):
        raise HTTPException(status_code=400, detail="mode 必须为 control 或 experiment")
    session_id = request.conversation_id or str(uuid.uuid4())
    anchor_date = _resolve_anchor_date(request.date, None)
    task_id = _create_assessment_task(
        request.user_id, request.mode, session_id, anchor_date, background_tasks)
    api_logger.info(f"[/plan] 创建任务 {task_id} user={request.user_id} mode={request.mode} date={anchor_date}")
    return PlanResponse(task_id=task_id, status="started",
                        message="健康决策任务已启动，请用 task_id 轮询 /status")


# --------------------------- /status ---------------------------
@app.get("/status/{task_id}", response_model=StatusResponse)
async def get_status(task_id: str):
    """查询健康决策任务状态与报告结果。"""
    task = assessment_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return StatusResponse(task_id=task_id, status=task["status"], progress=task["progress"],
                          message=task["message"], result=task.get("result"))


@app.get("/dashboard/{user_id}")
async def get_dashboard(user_id: int, on_date: Optional[str] = Query(default=None, alias="date")):
    """看板数据（纯数据库聚合，无 LLM、毫秒级）：KPI/身体/睡眠/饮食/运动/周对比。

    Query:
        date: 锚点日期 YYYY-MM-DD，默认今天；以该日为「当日」面板并计算周对比。

    供"非报告类看板"页面秒开使用；不触发多智能体工作流。
    """
    data = await asyncio.to_thread(hdata.get_week_overview, user_id, 14, on_date)
    return {"user_id": user_id, "date": on_date or date.today().isoformat(), "dashboard": data}


# --------------------------- 三页只读 + 睡眠录入端点 ---------------------------


@app.get("/sleep/{user_id}", response_model=SleepOverviewResponse)
async def get_sleep(user_id: int, range: str = "7d"):
    """睡眠监测页数据聚合。

    Query:
        range: 趋势天数，"7d" 或 "14d"，默认 7d

    返回 sleep 对象 + sources 标注，字段说明见 docs/接口契约.md。
    """
    days = 14 if range.rstrip("dD") == "14" else 7
    data = await asyncio.to_thread(hdata.get_sleep_overview, user_id, days)
    return data


@app.post("/sleep/entry", response_model=SleepEntryResponse)
async def create_sleep_entry(req: SleepEntryRequest):
    """手动录入睡眠记录（写入 watch_data.sleep_data JSONB）。

    Body:
        bedtime (必填): ISO 入睡时间
        wake_time (必填): ISO 起床时间
        nap_minutes (可选): 小憩分钟数
        user_id (可选): 用户 ID，默认 1
        on_date (可选): 日期，默认今天

    无 DDL、无表创建；同日有行则合并更新 JSONB，无行则插入最小行。
    """
    try:
        result = await asyncio.to_thread(
            hdata.save_sleep_entry,
            req.user_id, req.bedtime, req.wake_time, req.nap_minutes, req.on_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return SleepEntryResponse(saved=result["saved"], sleep_data=result["sleep_data"])


@app.get("/exercise/{user_id}", response_model=ExerciseOverviewResponse)
async def get_exercise(user_id: int):
    """运动分析页数据聚合。

    返回 exercise 对象 + sources 标注，字段说明见 docs/接口契约.md。
    """
    data = await asyncio.to_thread(hdata.get_exercise_overview, user_id)
    return data


@app.get("/nutrition/{user_id}", response_model=NutritionOverviewResponse)
async def get_nutrition(user_id: int, date: Optional[str] = None):
    """饮食管理页数据聚合。

    Query:
        date: 日期 YYYY-MM-DD，默认今天

    返回 nutrition 对象 + sources 标注，字段说明见 docs/接口契约.md。
    """
    data = await asyncio.to_thread(hdata.get_nutrition_overview, user_id, date)
    return data


@app.get("/report/latest/{user_id}")
async def get_latest_report(user_id: int, on_date: Optional[str] = Query(default=None, alias="date")):
    """查询某用户已生成的报告（读 ai_conversations 落库缓存，免重复跑工作流）。

    Query:
        date: 可选，按报告锚点日筛选；缺省返回最近一次。

    返回结构与 /status 的 result 一致（含 final_report.chart_data），并标记 source=cache。
    若该用户尚无报告，返回 404。
    """
    if on_date:
        try:
            date.fromisoformat(on_date)
        except ValueError as e:
            raise HTTPException(status_code=422, detail="date 格式须为 YYYY-MM-DD") from e
    result = await load_latest_assessment(user_id, on_date)
    if not result:
        raise HTTPException(status_code=404, detail="该用户暂无已生成的报告，请先调用 /plan 生成")
    return result


@app.get("/tasks")
async def list_tasks():
    """列出全部任务摘要。"""
    return {"tasks": [
        {"task_id": tid, "status": t["status"], "mode": t.get("mode"),
         "created_at": t.get("created_at")}
        for tid, t in assessment_tasks.items()
    ]}


# --------------------------- 会话历史接口 ---------------------------
@app.get("/conversations")
async def list_conversations():
    """会话列表（存于 ai_conversations），按最近更新倒序。"""
    return await get_store().list_conversations()


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """查询指定会话历史。"""
    history = await get_store().get_history(conversation_id)
    return {"conversation_id": conversation_id, "messages": history}


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """清空指定会话。"""
    await get_store().clear(conversation_id)
    return {"conversation_id": conversation_id, "status": "cleared"}


# --------------------------- ASR 语音转文字 ---------------------------
@app.post("/asr")
async def asr(audio: UploadFile = File(...), audio_format: str = Form(default="", alias="format")):
    """语音转文字端点。

    multipart/form-data:
        audio: 录音文件（webm/opus 等）
        format: MIME 类型（如 audio/webm;codecs=opus）

    返回: {"text": str, "duration_ms": int|None, "model": str}
    """
    if not audio or not audio.filename:
        raise HTTPException(status_code=422, detail={"error": "未上传音频文件"})

    mime = (audio_format or audio.content_type or "audio/webm").split(";")[0].strip()

    max_bytes = int(config.ASR_MAX_MB * 1024 * 1024)

    # 优先用 Starlette UploadFile.size 判大小（避免先全读再判内存峰值）
    if hasattr(audio, "size") and audio.size is not None and audio.size > max_bytes:
        raise HTTPException(
            status_code=422,
            detail={"error": f"音频文件过大（最大 {config.ASR_MAX_MB}MB）"},
        )

    # 分块读取，累计超限立即中止（无 .size 或 .size 不可信时兜底）
    try:
        buf = bytearray()
        while chunk := await audio.read(1 << 20):  # 1MB 步进
            buf.extend(chunk)
            if len(buf) > max_bytes:
                raise HTTPException(
                    status_code=422,
                    detail={"error": f"音频文件过大（最大 {config.ASR_MAX_MB}MB）"},
                )
        data = bytes(buf)
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"[/asr] 读取音频失败: {e}")
        raise HTTPException(status_code=422, detail={"error": f"读取音频文件失败: {e}"})

    if not data:
        raise HTTPException(status_code=422, detail={"error": "音频文件为空"})

    api_logger.info(f"[/asr] 收到音频 {audio.filename} mime={mime} size={len(data)}")

    # 异步调用 ASR（同步 IO 包到线程池；时长校验在 transcribe_audio 内部尽力估算）
    try:
        result = await asyncio.to_thread(transcribe_audio, data, mime, audio.filename or "recording.webm")
    except ASRValidationError as e:
        api_logger.warning(f"[/asr] 校验失败: {e}")
        raise HTTPException(status_code=e.status_code, detail={"error": str(e)})
    except ASRError as e:
        api_logger.error(f"[/asr] ASR 服务异常: {e}")
        raise HTTPException(status_code=e.status_code, detail={"error": str(e)})
    except Exception as e:
        api_logger.error(f"[/asr] 未知异常: {e}")
        raise HTTPException(status_code=500, detail={"error": f"ASR 服务内部错误: {e}"})

    api_logger.info(f"[/asr] 转写结果 model={result.get('model')} text_len={len(result.get('text',''))}")
    return result


# --------------------------- TTS 语音合成 ---------------------------
class TTSRequest(BaseModel):
    text: str = Field(..., description="待合成文本", min_length=1)


@app.post("/tts")
async def tts_synthesize(request: TTSRequest):
    """语音合成端点。

    JSON body:
        {"text": "每日30分钟有氧搭配15分钟力量..."}

    返回: audio/mpeg 二进制音频数据
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=422, detail={"error": "文本为空"})

    api_logger.info(f"[/tts] 合成请求 text_len={len(request.text)}")

    try:
        audio_data = await asyncio.to_thread(synthesize_speech, request.text.strip())
    except TTSValidationError as e:
        api_logger.warning(f"[/tts] 校验失败: {e}")
        raise HTTPException(status_code=e.status_code, detail={"error": str(e)})
    except TTSError as e:
        api_logger.error(f"[/tts] TTS 服务异常: {e}")
        raise HTTPException(status_code=e.status_code, detail={"error": str(e)})
    except Exception as e:
        api_logger.error(f"[/tts] 未知异常: {e}")
        raise HTTPException(status_code=500, detail={"error": f"TTS 服务内部错误: {e}"})

    api_logger.info(f"[/tts] 合成成功 audio_bytes={len(audio_data)}")
    from fastapi.responses import Response
    return Response(content=audio_data, media_type="audio/mpeg")


# --------------------------- Image 报告图片生成 ---------------------------
class ReportImageRequest(BaseModel):
    kpi: dict = Field(default_factory=dict, description="KPI 卡片数据")
    body: dict = Field(default_factory=dict, description="身体指标数据")
    sleep: dict = Field(default_factory=dict, description="睡眠监测数据")
    nutrition: dict = Field(default_factory=dict, description="饮食监测数据")
    exercise: dict = Field(default_factory=dict, description="运动监测数据")
    healthAdvice: dict = Field(default_factory=dict, description="健康建议文本")


@app.post("/report-image")
async def report_image_generate(request: ReportImageRequest):
    """报告图片生成端点。

    JSON body:
        { "kpi": {...}, "body": {...}, "sleep": {...}, ... }

    返回: image/png 二进制图片数据
    """
    data = request.model_dump()
    if not data:
        raise HTTPException(status_code=422, detail={"error": "报告数据为空"})

    api_logger.info(f"[/api/report-image] 生成请求 kpi_keys={list(data.get('kpi', {}).keys())}")

    try:
        img_data = await asyncio.to_thread(generate_report_image, data)
    except ImageGenValidationError as e:
        api_logger.warning(f"[/api/report-image] 校验失败: {e}")
        raise HTTPException(status_code=e.status_code, detail={"error": str(e)})
    except ImageGenError as e:
        api_logger.error(f"[/api/report-image] 图片生成异常: {e}")
        raise HTTPException(status_code=e.status_code, detail={"error": str(e)})
    except Exception as e:
        api_logger.error(f"[/api/report-image] 未知异常: {e}")
        raise HTTPException(status_code=500, detail={"error": f"图片生成内部错误: {e}"})

    api_logger.info(f"[/api/report-image] 生成成功 img_bytes={len(img_data)}")
    from fastapi.responses import Response
    return Response(content=img_data, media_type="image/png")


# --------------------------- 健康检查 / 信息 ---------------------------
@app.get("/health")
async def health_check():
    return {
        "status": "healthy" if config.OPENAI_API_KEY else "warning",
        "llm_model": config.OPENAI_MODEL,
        "api_key_configured": bool(config.OPENAI_API_KEY),
        "active_tasks": len(assessment_tasks),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/")
async def root():
    return {
        "name": "暴汗艺术家 - 健康决策助手",
        "version": "3.0.0",
        "agents": ["生理评估", "运动教练", "膳食规划", "安全审计(预留)", "报告生成"],
        "endpoints": {
            "chat": "/chat - 任务型对话(报告/数据录入)",
            "plan": "/plan - 一键生成健康报告",
            "status": "/status/{task_id} - 查询任务状态(报告一次性获取)",
            "dashboard": "/dashboard/{user_id} - 看板数据聚合(纯DB)",
            "sleep": "/sleep/{user_id} - 睡眠监测页数据聚合(纯DB+mock)",
            "exercise": "/exercise/{user_id} - 运动分析页数据聚合(纯DB+mock)",
            "nutrition": "/nutrition/{user_id} - 饮食管理页数据聚合(纯DB+mock, 含date参数)",
            "sleep_entry": "/sleep/entry - 手动录入睡眠记录(POST, 写watch_data JSONB)",
            "report_latest": "/report/latest/{user_id} - 最近一次报告(落库缓存)",
            "asr": "/asr - 语音转文字(千问ASR)",
            "tts": "/tts - 文字转语音(大模型TTS)",
            "report_image": "/report-image - 报告数据转图片(大模型Image Gen)",
            "conversations": "/conversations - 会话历史",
            "docs": "/docs - API文档",
        },
    }


if __name__ == "__main__":
    api_logger.info("启动「暴汗艺术家」健康决策 API 服务…")
    uvicorn.run(app, host="0.0.0.0", port=8000)
