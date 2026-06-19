# HPU 5800 期末项目 · 作业材料索引

> **暴汗艺术家（Physio Artisan）** — 自主代理式多模态健康决策智能体  
> Health Personal Unit | 健身 × 饮食 × 睡眠 综合管理系统

本目录存放 HPU 期末项目（30%）的提交材料、作业要求参考与答辩用图表。**主报告正文见 [`期末项目报告.md`](./期末项目报告.md)**。

---

## 参考文档

| 文件 | 说明 |
| :--- | :--- |
| [`【小组作业-30%】期末项目 - Final Project 详细要求参考.pdf`](./【小组作业-30%】期末项目%20-%20Final%20Project%20详细要求参考.pdf) | 课程作业详细要求与评分维度 |
| [`[5800][30分]期末项目_自主代理式多模态人工智能解决方案.pdf`](./%5B5800%5D%5B30分%5D期末项目_自主代理式多模态人工智能解决方案.pdf) | 5800 期末项目说明（30 分） |
| [`../「暴汗艺术家」项目设计方案 v1.0.md`](../「暴汗艺术家」项目设计方案%20v1.0.md) | 项目整体设计（虚拟用户、对照/实验组、架构） |
| [`../接口契约.md`](../接口契约.md) | 前后端 API 契约 |

---

## 提交物

| 文件 | 状态 | 说明 |
| :--- | :---: | :--- |
| [`期末项目报告.md`](./期末项目报告.md) | ✅ 主稿 | Markdown 报告，含架构、代码摘录、作业对照清单 |
| [`期末项目报告.docx`](./期末项目报告.docx) | 待更新 | Word 版（由 MD 导出后微调排版） |
| `diagrams/*.png` | ✅ | 答辩/报告用插图（见下表，**勿改源 `.mmd`**） |
| 同伴评价 | ⚠ 单独交 | 每位组员单独提交，不放进本报告 |
| 演示视频 | ⭕ 可选 | Extra Credit，脚本提纲见报告 §12 |

转 PDF 前：全文搜索「待补充」，替换为真实姓名、截图与实测证据后再删除标注图例。

---

## 作业要求 ↔ 项目落地对照

| 作业要求项 | 评分维度 | 报告章节 | 关键源码 |
| :--- | :--- | :--- | :--- |
| 小组成员姓名 | 展示与清晰度 | §1 + 封面 | — |
| 问题陈述 | 15′ | §2 §3 | — |
| 系统提示词 | 20′ | §4 | `backend/agents/health_prompts.py` |
| 代理式工作流 | 9′ | §5 | `backend/agents/langgraph_agents.py` |
| 工具 / 函数调用 | 9′ | §6 | `backend/agents/health_tools.py` |
| 多模态组件 | 6′ | §7 | `report_payload.py` `image_gen.py` `tts.py` |
| 安全与伦理 + 压测 | 6′ | §8 §9 | `safety.py` `guardrails.py` |
| 技术反思 | 清晰度 | §10 | — |
| 部署与评估（加分） | +5′ | §11 | `api_server.py` |
| 视频展示（加分） | +5′ | §12 | 可选 |

完整自检表见 [`期末项目报告.md` §0](期末项目报告.md#0-作业要求对照清单提交前自检-checklist)。

---

## 核心智能体（LangGraph 单向 StateGraph）

编排为**单向流水线**，无中央协调员；条件边由 `physio_evaluator` 输出的疲劳等级驱动。

| 节点 | 职责 |
| :--- | :--- |
| `data_loader` | 数据接入：DB 优先 + mock 回退 + 确定性公式 |
| `physio_evaluator` | 生理评估：CoT 解读 RS / 疲劳红旗 |
| `exercise_coach` | 运动教练：疲劳高/中时调用 wger 降载 |
| `maintain_plan` | 维持/进阶力量计划：疲劳低时触发 |
| `nutrition_planner` | 膳食规划：调用 USDA 工具配平 |
| `sleep_advisor` | 睡眠恢复与作息建议 |
| `guardrail_auditor` | 安全审计：screen_text 红线扫描，命中则熔断 |
| `report_generator` | 多模态报告：visual_metrics + vocal_narrative |

简化链路：

```
用户请求 → data_loader → physio_evaluator → [疲劳高/中: exercise_coach | 疲劳低: maintain_plan]
         → nutrition_planner → sleep_advisor → guardrail_auditor → report_generator → 多模态报告
```

---

## 图表索引（`diagrams/`）

报告内通过相对路径引用 PNG；源文件为 Mermaid（`.mmd`），**本 README 不修改流程图文件**。

| 图号 | 文件 | 内容 |
| :--- | :--- | :--- |
| 图 4-1 | `01-提示词分层.png` | 六层系统提示词与 CoT 约束 |
| 图 5-1 | `02-工作流StateGraph.png` | LangGraph 有状态工作流（条件边） |
| 图 5-2 | `03-PTOR循环.png` | Plan → Tool → Observation → Revision → Final |
| 图 7-x | `04-多模态架构.png` | chart_data / 图片报告 / TTS / ASR |
| 图 8-1 | `05-安全防御纵深.png` | 输入预检 + 输出审计双层护栏 |

重新导出 PNG（可选）：

```powershell
cd docs/works/diagrams
node _extract.js   # 需本地 puppeteer 环境，见 puppeteer.json
```

---

## 关键代码速查

```
backend/agents/langgraph_agents.py   # StateGraph 节点注册与条件边
backend/agents/health_prompts.py     # 分层提示词与 CoT
backend/agents/health_tools.py         # wger / USDA / 生理公式工具
backend/agents/report_payload.py       # chart_data 多模态契约
backend/agents/safety.py               # 输入侧 screen_text
backend/agents/guardrails.py           # 输出侧 guardrail_auditor
backend/api_server.py                  # /chat /plan /report-image /tts /asr
frontend/src/views/                    # 睡眠 / 运动 / 营养 / 报告页
```

---

## 待团队补充（提交前）

详见 [`期末项目报告.md` §0.0](期末项目报告.md#00-全文待补充事项汇总清单) 汇总表，主要包括：

- **组长**：封面组员/学号、课程名、日期、分工、参考文献
- **产品**：用户画像、部署形态、指标目标值
- **前端**：看板/报告页/图表/会诊室/语音条 **真实运行截图**
- **测试**：安全熔断与五类压测 **实测截图或日志**
- **后端**：真实 API 接入或部署参数（如有）

---

## 项目一句话

分析穿戴设备与自报健康数据，经 LangGraph 多智能体按思维链协同推理，自主调用工具，生成「可视化图表 + 图片信息图 + 语音简报」的闭环健康决策报告。
