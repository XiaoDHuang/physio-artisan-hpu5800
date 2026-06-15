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

from fastapi import FastAPI, HTTPException, BackgroundTasks
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


class PlanRequest(BaseModel):
    user_id: int = Field(default=intake.DEFAULT_USER_ID, description="用户ID，默认演示用户(小明 id=1)")
    mode: str = Field(default="control", description="场景：control(放任恶化) | experiment(积极恢复)")
    conversation_id: Optional[str] = Field(default=None, description="可选：关联的会话ID")


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
  "mode": "control | experiment | null",
  "reply": "面向用户的简短中文话术"
}

字段名规范：duration_minutes, peak_hr, hr_60s, rpe, diet_narrative, weight_kg, body_fat_pct。"""


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


# --------------------------- 后台任务：运行健康决策工作流 ---------------------------
async def run_assessment_task(task_id: str, user_id: int, mode: str, session_id: str):
    try:
        assessment_tasks[task_id].update(status="processing", progress=20,
                                          message="多智能体会诊中：生理评估 → 教练 → 膳食 → 报告...")
        result = await asyncio.to_thread(
            lambda: get_agents().run_health_assessment(
                {"user_id": user_id, "mode": mode, "session_id": session_id})
        )
        if result.get("success"):
            assessment_tasks[task_id].update(status="completed", progress=100,
                                             message="健康决策完成！", result=result)
            # 报告产出回写到 ai_conversations（同 session_id 行）
            try:
                await save_assessment_artifacts(session_id, user_id, result)
            except Exception as e:  # noqa: BLE001
                api_logger.error(f"任务 {task_id} 产出回写失败: {e}")
            # 训练/睡眠/饮食计划回写到 user_plans（三页建议/方案源）
            try:
                from datetime import date as _date
                await save_user_plan(user_id, _date.today().isoformat(), result)
            except Exception as e:  # noqa: BLE001
                api_logger.error(f"任务 {task_id} user_plans 回写失败: {e}")
        else:
            assessment_tasks[task_id].update(status="failed", progress=100,
                                             message=result.get("error", "未知错误"), result=result)
    except Exception as e:  # noqa: BLE001
        api_logger.error(f"任务 {task_id} 执行异常: {e}")
        assessment_tasks[task_id].update(status="failed", progress=100, message=f"系统错误: {e}")


def _create_assessment_task(user_id: int, mode: str, session_id: str,
                            background_tasks: BackgroundTasks) -> str:
    task_id = str(uuid.uuid4())
    assessment_tasks[task_id] = {
        "task_id": task_id, "status": "started", "progress": 0,
        "message": "任务已创建，准备开始健康决策...", "result": None,
        "created_at": datetime.now().isoformat(),
        "user_id": user_id, "mode": mode, "session_id": session_id,
    }
    background_tasks.add_task(run_assessment_task, task_id, user_id, mode, session_id)
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
                                  intake.DEFAULT_USER_ID)
        except Exception as e:  # noqa: BLE001
            api_logger.error(f"安全日志写入失败: {e}")
        await store.append(conversation_id, [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": block_reply},
        ])
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
        task_id = _create_assessment_task(intake.DEFAULT_USER_ID, mode, conversation_id, background_tasks)
        resp.task_id = task_id
        resp.can_proceed = True
        resp.reply = (reply or "好的，正在为你生成健康体检报告。") + \
            f"\n\n🤖 多智能体会诊已启动（task_id={task_id}），稍后用 /status 查看报告。"

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
                    intake.save_entry, data_type, cleaned, intake.DEFAULT_USER_ID)
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
    ])
    return resp


# --------------------------- /plan ---------------------------
@app.post("/plan", response_model=PlanResponse)
async def create_plan(request: PlanRequest, background_tasks: BackgroundTasks):
    """一键生成健康决策报告（异步）。前端"一键生成"按钮直接调用本接口。"""
    if request.mode not in ("control", "experiment"):
        raise HTTPException(status_code=400, detail="mode 必须为 control 或 experiment")
    session_id = request.conversation_id or str(uuid.uuid4())
    task_id = _create_assessment_task(request.user_id, request.mode, session_id, background_tasks)
    api_logger.info(f"[/plan] 创建任务 {task_id} user={request.user_id} mode={request.mode}")
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
async def get_dashboard(user_id: int):
    """看板数据（纯数据库聚合，无 LLM、毫秒级）：KPI/身体/睡眠/饮食/运动/周对比。

    供"非报告类看板"页面秒开使用；不触发多智能体工作流。
    """
    data = await asyncio.to_thread(hdata.get_week_overview, user_id)
    return {"user_id": user_id, "dashboard": data}


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
async def get_latest_report(user_id: int):
    """查询某用户最近一次已生成的报告（读 ai_conversations 落库缓存，免重复跑工作流）。

    返回结构与 /status 的 result 一致（含 final_report.chart_data），并标记 source=cache。
    若该用户尚无报告，返回 404。
    """
    result = await load_latest_assessment(user_id)
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
            "conversations": "/conversations - 会话历史",
            "docs": "/docs - API文档",
        },
    }


if __name__ == "__main__":
    api_logger.info("启动「暴汗艺术家」健康决策 API 服务…")
    uvicorn.run(app, host="0.0.0.0", port=8000)
