"""
「暴汗艺术家」LangGraph 多智能体健康决策系统

本模块用真·LangGraph `StateGraph` 实现设计方案 §4.1 的有状态工作流：

    data_loader ─▶ physio_evaluator ─┬─(疲劳 高/中)─▶ exercise_coach ─▶ nutrition_planner ─┐
                                     │                                                      ├─▶ guardrail_auditor ─▶ report_generator ─▶ END
                                     └─(疲劳 低)──────▶ maintain_plan ───────────────────────┘

五个专家智能体（各持独立 CoT 提示词）：
1. physio_evaluator   生理评估智能体  —— 解读硬编码 RS/疲劳红旗，输出疲劳等级
2. exercise_coach     运动教练智能体  —— 高疲劳日降载，调用 wger 工具检索低负荷动作
3. nutrition_planner  膳食规划智能体  —— 调用 USDA 工具配平高蛋白，含油脂代偿
4. guardrail_auditor  安全审计智能体  —— 【本期仅预留占位，直通放行，不做拦截实现】
5. report_generator   报告生成智能体  —— 汇总多模态 JSON(visual_metrics + vocal_narrative)

设计要点：
- 条件边由生理评估输出的 `fatigue_level` 动态决定是否触发降载/营养干预。
- 所有生理数字由 health_tools 的确定性公式计算，LLM 只负责解读与文案，拒绝口算。
- 工具调用本期为本地 mock（health_tools），函数签名与真实 API 一致，便于后续替换。

适用于大模型技术初级用户：
- StateGraph 把"谁先干、谁后干、什么条件下分叉"显式画成一张图。
- 每个节点是一个函数：读共享状态 -> 调用 LLM/工具 -> 写回共享状态。
"""

from __future__ import annotations

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# 添加 backend 目录到 Python 路径，保证以脚本方式运行时可导入同级包
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.langgraph_config import langgraph_config as config
from agents import health_tools as tools
from agents import health_data as hdata
from agents.health_prompts import (
    load_prompt,
    GUARDRAIL_BLOCK_TEMPLATE,
)
from agents.observability import (
    get_langfuse_client,
    build_callback_handler,
    build_run_config,
    flush_langfuse,
)


# --------------------------- 日志配置 ---------------------------
def setup_agents_logger() -> logging.Logger:
    logger = logging.getLogger("health_agents")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        fh = logging.FileHandler("logs/backend.log", encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(fh)
    return logger


agents_logger = setup_agents_logger()


# =============================================================================
# 共享状态定义
# =============================================================================
class HealthAgentState(TypedDict):
    """多智能体共享状态（在各节点间流转）。"""
    messages: Annotated[List[Any], add_messages]

    # 输入
    user_id: int
    mode: str                       # control | experiment
    user_query: str                 # 用户自由提问（可选，供安全审计/报告参考）

    # 数据接入层产出
    snapshot: Dict[str, Any]        # 原始指标快照(health_data)
    derived: Dict[str, Any]         # 确定性公式派生指标(RS/HRR/TRIMP/疲劳红旗)

    # 各智能体产出
    physio_assessment: Dict[str, Any]
    fatigue_level: str              # high | medium | low —— 条件边依据
    training_plan: Dict[str, Any]
    meal_plan: Dict[str, Any]
    sleep_advice: Dict[str, Any]
    safety_result: Dict[str, Any]
    final_report: Dict[str, Any]

    # 过程记录（供"智能体会诊室"UI 展示）
    agent_outputs: Dict[str, Any]
    reasoning_chain: List[str]
    current_agent: str
    iteration_count: int
    status: str


# =============================================================================
# 工具函数：稳健的 JSON 解析
# =============================================================================
def _parse_json(content: str) -> Dict[str, Any]:
    """从 LLM 输出中稳健提取 JSON（容忍 ```json 包裹与多余文字）。"""
    if not content:
        return {}
    text = content.strip()
    if "```" in text:
        # 去掉 markdown 代码围栏
        parts = text.split("```")
        for p in parts:
            p = p.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                text = p
                break
    # 截取首个 { ... } 区间
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    try:
        return json.loads(text)
    except Exception:  # noqa: BLE001
        return {}


# =============================================================================
# 多智能体系统主类
# =============================================================================
class LangGraphHealthAgents:
    """基于 LangGraph 的「暴汗艺术家」多智能体健康决策系统。"""

    def __init__(self):
        llm_config = config.get_llm_config()
        self.llm = ChatOpenAI(**llm_config)
        self.graph = self._create_agent_graph()
        # Langfuse 可观测性客户端（None 表示未启用/不可用 -> 自动无追踪运行）
        self.langfuse = get_langfuse_client()

    # ---------------------------------------------------------------------
    # 工作流图构建
    # ---------------------------------------------------------------------
    def _create_agent_graph(self):
        workflow = StateGraph(HealthAgentState)

        workflow.add_node("data_loader", self._data_loader_node)
        workflow.add_node("physio_evaluator", self._physio_evaluator_node)
        workflow.add_node("exercise_coach", self._exercise_coach_node)
        workflow.add_node("nutrition_planner", self._nutrition_planner_node)
        workflow.add_node("maintain_plan", self._maintain_plan_node)
        workflow.add_node("sleep_advisor", self._sleep_advisor_node)
        workflow.add_node("guardrail_auditor", self._guardrail_auditor_node)
        workflow.add_node("report_generator", self._report_generator_node)

        # 入口：数据接入 -> 生理评估
        workflow.set_entry_point("data_loader")
        workflow.add_edge("data_loader", "physio_evaluator")

        # 条件边：由疲劳等级决定是否触发降载干预
        workflow.add_conditional_edges(
            "physio_evaluator",
            self._route_by_fatigue,
            {
                "intervene": "exercise_coach",   # 高/中疲劳 -> 降载
                "maintain": "maintain_plan",     # 低疲劳 -> 维持
            },
        )

        # 干预路径：教练 -> 营养 -> 睡眠建议
        workflow.add_edge("exercise_coach", "nutrition_planner")
        workflow.add_edge("nutrition_planner", "sleep_advisor")
        # 维持路径：维持 -> 睡眠建议
        workflow.add_edge("maintain_plan", "sleep_advisor")

        # 睡眠建议 -> 安全审计 -> 报告生成 -> 结束
        workflow.add_edge("sleep_advisor", "guardrail_auditor")
        workflow.add_edge("guardrail_auditor", "report_generator")
        workflow.add_edge("report_generator", END)

        return workflow.compile()

    # ---------------------------------------------------------------------
    # 通用 LLM 调用（含异常回退）
    # ---------------------------------------------------------------------
    def _invoke_llm(self, system_prompt: str, user_hint: str = "") -> str:
        messages = [SystemMessage(content=system_prompt)]
        if user_hint:
            messages.append(HumanMessage(content=user_hint))
        try:
            resp = self.llm.invoke(messages)
            return resp.content or ""
        except Exception as e:  # noqa: BLE001
            agents_logger.error("[LLM] 调用失败: %s", e)
            return ""

    # ---------------------------------------------------------------------
    # 节点 0：数据接入层（DB 优先 + mock 回退 + 硬编码公式）
    # ---------------------------------------------------------------------
    def _data_loader_node(self, state: HealthAgentState) -> HealthAgentState:
        user_id = state.get("user_id", 1)
        mode = state.get("mode", "control")

        # 复用确定性派生（与报告双场景对比同源，避免逻辑漂移）
        m = hdata.compute_metrics(user_id, mode)
        snap, derived = m["snapshot"], m["derived"]

        chain = state.get("reasoning_chain", [])
        chain.append(
            f"[数据接入] user={user_id} mode={mode} 来源={snap['sources']} | "
            f"RS={derived['rs']} HRR={derived['hrr']} TRIMP={derived['trimp']} "
            f"疲劳红旗={derived['flag_count']}项 -> {derived['fatigue']}"
        )

        new_state = state.copy()
        new_state["snapshot"] = snap
        new_state["derived"] = derived
        new_state["reasoning_chain"] = chain
        new_state["current_agent"] = "data_loader"
        new_state["status"] = "running"
        agents_logger.info("[DataLoader] %s", chain[-1])
        return new_state

    # ---------------------------------------------------------------------
    # 节点 1：生理评估智能体
    # ---------------------------------------------------------------------
    def _physio_evaluator_node(self, state: HealthAgentState) -> HealthAgentState:
        snap, d = state["snapshot"], state["derived"]
        prompt = load_prompt("physio_evaluator").format(
            sleep_score=snap["sleep_score"], hrv_today=snap["hrv_today"],
            hrv_baseline=d["hrv_baseline"], rhr_today=snap["rhr_today"],
            rhr_baseline=d["rhr_baseline"], hrr=d["hrr"], trimp=d["trimp"],
            rs=d["rs"], flag_count=d["flag_count"],
            flag_list="; ".join(d["flags"]) or "无",
        )
        content = self._invoke_llm(prompt)
        parsed = _parse_json(content)

        # 以确定性公式为准兜底，LLM 仅补充 insight 文案
        assessment = {
            "rs": d["rs"],
            "fatigue": parsed.get("fatigue", d["fatigue"]) if parsed.get("fatigue") in ("high", "medium", "low") else d["fatigue"],
            "rhr_status": parsed.get("rhr_status", d["rhr_status"]),
            "insight": parsed.get("insight") or self._fallback_insight(d),
            "hrr": d["hrr"], "trimp": d["trimp"],
        }

        return self._commit(state, "physio_evaluator", assessment,
                            extra={"physio_assessment": assessment,
                                   "fatigue_level": assessment["fatigue"]},
                            note=f"RS={d['rs']} 疲劳={assessment['fatigue']} | {assessment['insight']}")

    @staticmethod
    def _fallback_insight(d: Dict[str, Any]) -> str:
        if d["fatigue"] == "high":
            return "连续疲劳信号明显，中枢神经恢复差，今日必须运动降载。"
        if d["fatigue"] == "medium":
            return "出现部分疲劳信号，建议适度降低训练强度并关注恢复。"
        return "各项恢复指标良好，可维持原训练计划。"

    def _route_by_fatigue(self, state: HealthAgentState) -> str:
        """条件边：疲劳 高/中 -> 干预；低 -> 维持。"""
        fatigue = state.get("fatigue_level", "low")
        decision = "intervene" if fatigue in ("high", "medium") else "maintain"
        agents_logger.info("[Router] 疲劳=%s -> %s", fatigue, decision)
        state.setdefault("reasoning_chain", []).append(
            f"[条件边] 疲劳度={fatigue} -> {'触发降载干预' if decision == 'intervene' else '维持原计划'}"
        )
        return decision

    # ---------------------------------------------------------------------
    # 节点 2：运动教练智能体（高/中疲劳路径）
    # ---------------------------------------------------------------------
    def _exercise_coach_node(self, state: HealthAgentState) -> HealthAgentState:
        d = state["derived"]
        # 自主调用 wger 工具检索低负荷降载方案（含组数/次数/时长处方）
        wger_result = tools.wger_exercise_search.invoke({"query": "core stretch mobility", "limit": 3})

        prompt = load_prompt("exercise_coach").format(
            physio_json=json.dumps(state["physio_assessment"], ensure_ascii=False),
            trimp=d["trimp"], wger_result=json.dumps(wger_result, ensure_ascii=False),
        )
        parsed = _parse_json(self._invoke_llm(prompt))

        # 结构化动作（组数/次数/时长来自 wger 处方，确定性，不依赖 LLM 填）
        exercises = self._structured_exercises(wger_result)
        goals = self._user_goals(state)
        plan = {
            "training_type": parsed.get("training_type", "recovery"),
            "exercises": exercises,
            "reason": parsed.get("reason") or "中枢疲劳偏高，改用核心稳定与拉伸代替大重量深蹲，防止代偿受伤。",
            "recommended_duration": goals.get("exercise_duration_target", "30-40"),
            "calorie_target": goals.get("calorie_burn_session_target", "200-300"),
            "source": parsed.get("source", "wger_api"),
        }
        return self._commit(state, "exercise_coach", plan,
                            extra={"training_plan": plan},
                            tool_calls=[{"tool": "wger_exercise_search", "result": wger_result}],
                            note=f"降载[{plan['training_type']}]: {[e['name'] for e in exercises]}")

    @staticmethod
    def _structured_exercises(wger_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """把 wger 检索结果整理成 {name, sets, reps|duration_sec, muscles, description} 列表。"""
        out = []
        for e in wger_result.get("exercises", []):
            p = e.get("prescription", {})
            item = {"name": e["name"], "muscles": e.get("muscles", []),
                    "description": e.get("description", ""), "sets": p.get("sets")}
            if "reps" in p:
                item["reps"] = p["reps"]
            if "duration_sec" in p:
                item["duration_sec"] = p["duration_sec"]
            out.append(item)
        return out

    @staticmethod
    def _user_goals(state: HealthAgentState) -> Dict[str, Any]:
        """从用户画像取目标配置（用于推荐时长/消耗目标）。"""
        try:
            return hdata.get_user_profile(state.get("user_id", 1)).get("goals") or {}
        except Exception:  # noqa: BLE001
            return {}

    # ---------------------------------------------------------------------
    # 节点 2'：维持原计划（低疲劳路径）
    # ---------------------------------------------------------------------
    def _maintain_plan_node(self, state: HealthAgentState) -> HealthAgentState:
        d = state["derived"]
        # 维持/进阶：检索力量模板（深蹲/俯卧撑/硬拉/平板，含组数次数）
        wger_result = tools.wger_exercise_search.invoke({"query": "strength", "limit": 4})
        exercises = self._structured_exercises(wger_result)
        goals = self._user_goals(state)
        plan = {
            "training_type": "maintain",
            "exercises": exercises,
            "reason": f"准备度良好(RS={d['rs']})，恢复充分，可维持原中高强度力量训练。",
            "recommended_duration": goals.get("exercise_duration_target", "40-60"),
            "calorie_target": goals.get("calorie_burn_session_target", "320-450"),
            "source": "wger_api",
            "encouragement": "状态在线！今天可以继续暴汗，注意训练后拉伸与补水。",
        }
        return self._commit(state, "maintain_plan", plan,
                            extra={"training_plan": plan},
                            tool_calls=[{"tool": "wger_exercise_search", "result": wger_result}],
                            note=f"维持原计划 RS={d['rs']} -> {[e['name'] for e in exercises]}")

    # ---------------------------------------------------------------------
    # 节点 3：膳食规划智能体
    # ---------------------------------------------------------------------
    def _nutrition_planner_node(self, state: HealthAgentState) -> HealthAgentState:
        snap, d = state["snapshot"], state["derived"]
        sauce = tools.detect_sauce(snap["diet_narrative"])

        # 自主调用 USDA 工具检索关键食材（mock）
        usda_result = [
            tools.usda_food_search.invoke({"keyword": kw})
            for kw in ("salmon", "鸡胸肉", "糙米饭")
        ]

        prompt = load_prompt("nutrition_planner").format(
            tdee=d["tdee"], weight_kg=snap["weight_kg"],
            diet_narrative=snap["diet_narrative"], sauce_detected=sauce,
            usda_result=json.dumps(usda_result, ensure_ascii=False),
        )
        parsed = _parse_json(self._invoke_llm(prompt))

        protein_target = int(round(1.8 * snap["weight_kg"]))
        # 结构化三餐（餐别/食材/克数/单品热量），确定性组装，不依赖 LLM 填
        meal_struct = tools.build_meal_plan(tools.LAMBDA_SAUCE if sauce else 1.0)
        plan = {
            "total_calories": parsed.get("total_calories", max(1200, d["tdee"] - 300)),
            "protein_target_g": parsed.get("protein_target_g", protein_target),
            "diet_suggestion": parsed.get("diet_suggestion")
                or "晚餐建议补充150g煎三文鱼配糙米饭，已调用USDA数据库配平今日蛋白质缺口。",
            "meals": meal_struct["meals"],
            "day_total_calories": meal_struct["day_total_calories"],
            "day_total_protein": meal_struct["day_total_protein"],
            "sauce_compensation": tools.LAMBDA_SAUCE if sauce else 1.0,
            "source": parsed.get("source", "usda_api"),
        }
        return self._commit(state, "nutrition_planner", plan,
                            extra={"meal_plan": plan},
                            tool_calls=[{"tool": "usda_food_search", "result": usda_result}],
                            note=f"目标热量={plan['total_calories']}kcal 蛋白={plan['protein_target_g']}g "
                                 f"油脂代偿={'是' if sauce else '否'}")

    # ---------------------------------------------------------------------
    # 节点 3'：睡眠建议智能体
    # ---------------------------------------------------------------------
    def _sleep_advisor_node(self, state: HealthAgentState) -> HealthAgentState:
        snap = state["snapshot"]
        sleep_score = snap.get("sleep_score", 0)
        prompt = load_prompt("sleep_advisor").format(
            sleep_score=sleep_score,
            total_hours=round(max(5.0, sleep_score / 12.0 + 1.0), 1),
            deep_sleep_percent=max(8, min(28, int(sleep_score / 4))),
            rhr=snap.get("rhr_today", 60),
        )
        parsed = _parse_json(self._invoke_llm(prompt))
        advice = {
            "advice": parsed.get("advice") or self._fallback_sleep_advice(sleep_score),
            "focus": parsed.get("focus") or ("尽早入睡、保证深睡" if sleep_score < 75 else "保持规律作息"),
            "source": "rule_based",
        }
        return self._commit(state, "sleep_advisor", advice,
                            extra={"sleep_advice": advice},
                            note=f"睡眠建议(评分{sleep_score}): {advice['focus']}")

    @staticmethod
    def _fallback_sleep_advice(sleep_score: int) -> str:
        if sleep_score < 65:
            return "睡眠明显不足：固定 23 点前入睡，睡前 1 小时远离手机蓝光，卧室控温 20-22℃，午后忌咖啡因。"
        if sleep_score < 80:
            return "睡眠尚可但有提升空间：保持规律作息，睡前做 5 分钟拉伸放松，避免睡前剧烈运动与饱食。"
        return "睡眠良好：维持当前作息节律，周末也尽量同点起床，巩固深睡比例。"

    # ---------------------------------------------------------------------
    # 节点 4：安全审计智能体（输出审计，防御纵深）
    # ---------------------------------------------------------------------
    def _guardrail_auditor_node(self, state: HealthAgentState) -> HealthAgentState:
        from agents.safety import screen_text
        from store.safety_store import save_safety_log_sync

        # 审计上游产出 + 用户原始提问的合并文本
        combined = "\n".join([
            json.dumps(state.get("training_plan", {}), ensure_ascii=False),
            json.dumps(state.get("meal_plan", {}), ensure_ascii=False),
            state.get("user_query", "") or "",
        ])
        screen = screen_text(combined)
        blocked = screen["blocked"]

        result = {
            "status": "blocked" if blocked else "passed",
            "reason": screen["block_message"] if blocked else "未命中安全红线，[安全通行]。",
            "final_text": GUARDRAIL_BLOCK_TEMPLATE if blocked else "",
            "category": screen["category"], "level": screen["level"],
            "violations": screen["violations"], "warnings": screen["warnings"],
            "implemented": True,
        }

        # 命中红线或存在告警时写安全日志
        if blocked or screen["warnings"]:
            try:
                save_safety_log_sync(combined, screen["category"], screen["level"],
                                     screen["violations"], screen["warnings"], blocked,
                                     user_id=state.get("user_id", 1))
            except Exception as e:  # noqa: BLE001
                agents_logger.error("[Guardrail] 安全日志写入失败: %s", e)

        note = "安全审计 -> " + ("⛔ 拦截熔断" if blocked else "[安全通行]")
        return self._commit(state, "guardrail_auditor", result,
                            extra={"safety_result": result}, note=note)

    # ---------------------------------------------------------------------
    # 节点 5：报告生成智能体（多模态枢纽）
    # ---------------------------------------------------------------------
    def _report_generator_node(self, state: HealthAgentState) -> HealthAgentState:
        d = state["derived"]
        snap = state["snapshot"]

        # 安全拦截命中：跳过 LLM，直接输出就医分流熔断话术（仍保留 visual_metrics）
        safety = state.get("safety_result", {})
        if safety.get("status") == "blocked":
            report = {
                "visual_metrics": {"rs": d["rs"], "body_fat": snap["body_fat_pct"], "body_age": d["body_age"]},
                "vocal_narrative": safety.get("final_text") or GUARDRAIL_BLOCK_TEMPLATE,
                "safety_blocked": True,
            }
            new_state = self._commit(state, "report_generator", report,
                                     extra={"final_report": report},
                                     note="安全拦截 -> 输出就医分流话术")
            new_state["status"] = "completed"
            return new_state

        prompt = load_prompt("report_generator").format(
            physio_json=json.dumps(state.get("physio_assessment", {}), ensure_ascii=False),
            training_json=json.dumps(state.get("training_plan", {}), ensure_ascii=False),
            meal_json=json.dumps(state.get("meal_plan", {}), ensure_ascii=False),
            rs=d["rs"], body_fat=snap["body_fat_pct"], body_age=d["body_age"],
        )
        parsed = _parse_json(self._invoke_llm(prompt))

        report = {
            "visual_metrics": parsed.get("visual_metrics") or {
                "rs": d["rs"], "body_fat": snap["body_fat_pct"], "body_age": d["body_age"],
            },
            "vocal_narrative": parsed.get("vocal_narrative") or self._fallback_narrative(state),
        }
        new_state = self._commit(state, "report_generator", report,
                                 extra={"final_report": report},
                                 note="生成多模态体检报告")
        new_state["status"] = "completed"
        return new_state

    @staticmethod
    def _fallback_narrative(state: HealthAgentState) -> str:
        a = state.get("physio_assessment", {})
        return (
            f"早上好。今日准备度得分 {a.get('rs')}，{a.get('insight', '')}"
            "我已为你调整今日训练与膳食，记得跟练并按食谱补充蛋白质。"
            "本报告由AI生成，不能替代专业医疗诊断。如身体持续不适，请及时就医。"
        )

    # ---------------------------------------------------------------------
    # 状态提交辅助：统一写回 agent_outputs / reasoning_chain
    # ---------------------------------------------------------------------
    def _commit(self, state: HealthAgentState, agent: str, output: Dict[str, Any],
                extra: Optional[Dict[str, Any]] = None,
                tool_calls: Optional[List[Dict]] = None,
                note: str = "") -> HealthAgentState:
        new_state = state.copy()
        outputs = dict(state.get("agent_outputs", {}))
        outputs[agent] = {
            "output": output,
            "tool_calls": tool_calls or [],
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
        }
        new_state["agent_outputs"] = outputs

        chain = list(state.get("reasoning_chain", []))
        if note:
            chain.append(f"[{agent}] {note}")
        new_state["reasoning_chain"] = chain

        new_state["current_agent"] = agent
        new_state["iteration_count"] = state.get("iteration_count", 0) + 1
        if extra:
            new_state.update(extra)
        new_state["messages"] = state.get("messages", []) + [
            AIMessage(content=json.dumps(output, ensure_ascii=False))
        ]
        agents_logger.info("[%s] %s", agent, note)
        return new_state

    # ---------------------------------------------------------------------
    # 对外主入口
    # ---------------------------------------------------------------------
    def run_health_assessment(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """运行完整的多智能体健康决策工作流。

        Args:
            request: {
                "user_id": int,                 # 默认 1
                "mode": "control"|"experiment", # 默认 control(放任恶化, 高疲劳演示)
                "user_query": str,              # 可选, 用户自由提问
                "session_id": str               # 可选, 用于 Langfuse trace 按会话归组
            }
        Returns:
            {success, mode, physio_assessment, training_plan, meal_plan,
             safety_result, final_report, reasoning_chain, agent_outputs, ...}
        """
        user_id = request.get("user_id", 1)
        mode = request.get("mode", "control")
        user_query = request.get("user_query", "")
        session_id = request.get("session_id", "")

        initial_state: HealthAgentState = {
            "messages": [HumanMessage(content=f"请对 user={user_id} (mode={mode}) 进行健康决策评估")],
            "user_id": user_id, "mode": mode, "user_query": user_query,
            "snapshot": {}, "derived": {},
            "physio_assessment": {}, "fatigue_level": "low",
            "training_plan": {}, "meal_plan": {}, "sleep_advice": {},
            "safety_result": {}, "final_report": {},
            "agent_outputs": {}, "reasoning_chain": [],
            "current_agent": "", "iteration_count": 0, "status": "init",
        }

        # 构造 Langfuse 追踪配置（handler 为 None 时 run_config 为 None，行为同接入前）
        handler, _ = build_callback_handler(self.langfuse)
        run_config = build_run_config(
            handler, user_id=user_id, mode=mode, session_id=session_id,
        )

        try:
            final = self.graph.invoke(initial_state, config=run_config)
            result = {
                "success": True,
                "mode": mode,
                "physio_assessment": final.get("physio_assessment", {}),
                "fatigue_level": final.get("fatigue_level"),
                "training_plan": final.get("training_plan", {}),
                "meal_plan": final.get("meal_plan", {}),
                "sleep_advice": final.get("sleep_advice", {}),
                "safety_result": final.get("safety_result", {}),
                "final_report": final.get("final_report", {}),
                "derived_metrics": final.get("derived", {}),
                "data_sources": final.get("snapshot", {}).get("sources", {}),
                "reasoning_chain": final.get("reasoning_chain", []),
                "agent_outputs": final.get("agent_outputs", {}),
                "total_iterations": final.get("iteration_count", 0),
                "status": final.get("status", "completed"),
            }
            # 报告数据契约（前端渲染图表用）
            try:
                from agents.report_payload import build_report_payload
                if isinstance(result["final_report"], dict):
                    result["final_report"]["chart_data"] = build_report_payload(user_id, result)
            except Exception as e:  # noqa: BLE001
                agents_logger.error("[report_payload] 生成 chart_data 失败: %s", e)
            return result
        except Exception as e:  # noqa: BLE001
            agents_logger.error("[run_health_assessment] 工作流执行失败: %s", e)
            return {
                "success": False,
                "error": f"健康决策流程出错: {e}",
                "mode": mode,
                "final_report": {},
                "reasoning_chain": [],
                "agent_outputs": {},
                "status": "error",
            }
        finally:
            # 批处理任务：确保本次 trace 的事件在返回前刷入 Langfuse
            flush_langfuse(self.langfuse)

    def get_workflow_visualization(self) -> Dict[str, Any]:
        """返回工作流结构，供前端"智能体会诊室"渲染。"""
        return {
            "nodes": [
                {"id": "data_loader", "label": "数据接入", "icon": "🧹"},
                {"id": "physio_evaluator", "label": "生理评估智能体", "icon": "📊"},
                {"id": "exercise_coach", "label": "运动教练智能体", "icon": "🏋️"},
                {"id": "nutrition_planner", "label": "膳食规划智能体", "icon": "🍽️"},
                {"id": "maintain_plan", "label": "维持原计划", "icon": "✅"},
                {"id": "guardrail_auditor", "label": "安全审计智能体(预留)", "icon": "🛡️"},
                {"id": "report_generator", "label": "报告生成智能体", "icon": "📑"},
            ],
            "edges": [
                {"from": "data_loader", "to": "physio_evaluator"},
                {"from": "physio_evaluator", "to": "exercise_coach", "label": "疲劳 高/中"},
                {"from": "physio_evaluator", "to": "maintain_plan", "label": "疲劳 低"},
                {"from": "exercise_coach", "to": "nutrition_planner"},
                {"from": "nutrition_planner", "to": "guardrail_auditor"},
                {"from": "maintain_plan", "to": "guardrail_auditor"},
                {"from": "guardrail_auditor", "to": "report_generator"},
            ],
        }


# 便捷单例入口
def run_health_assessment(request: Dict[str, Any]) -> Dict[str, Any]:
    """模块级便捷函数：内部构造系统实例并运行。"""
    return LangGraphHealthAgents().run_health_assessment(request)


if __name__ == "__main__":
    # 简易冒烟测试（会真实调用 LLM；如需离线验证请见 README/验证脚本）
    import argparse

    parser = argparse.ArgumentParser(description="暴汗艺术家 多智能体健康决策")
    parser.add_argument("--user", type=int, default=1)
    parser.add_argument("--mode", choices=["control", "experiment"], default="control")
    args = parser.parse_args()

    result = run_health_assessment({"user_id": args.user, "mode": args.mode})
    print(json.dumps(result, ensure_ascii=False, indent=2))
