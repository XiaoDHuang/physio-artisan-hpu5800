# chat-report-by-date Specification

## Purpose

使 `POST /chat` 与 `POST /plan` 触发的多智能体健康报告，与报告页看板 `GET /dashboard/{user_id}?date=` 使用相同的用户与锚点日期语义。

## Requirements

### Requirement: Chat 请求携带用户与锚点日

系统 SHALL 在 `POST /chat` 请求体接受可选字段 `user_id`（int，默认 1）与 `date`（`YYYY-MM-DD`，默认今天）。报告意图（`intent=report`）SHALL 使用该 `user_id` 创建评估任务，不得写死默认演示用户。

#### Scenario: 报告页传入当前选中日期

- **WHEN** 前端 `POST /chat` 携带 `user_id=2`、`date=2026-06-15` 且意图为 report
- **THEN** 创建的评估任务使用 `user_id=2`、`anchor_date=2026-06-15`

#### Scenario: 缺省参数

- **WHEN** `POST /chat` 未传 `user_id` 与 `date` 且意图为 report
- **THEN** 使用 `user_id=1` 与今天作为锚点日

### Requirement: 锚点日解析优先级

系统 SHALL 按以下顺序确定报告锚点日：请求体 `date` > 意图路由抽取的 `on_date` > 今天。日期格式非法 SHALL 返回 422；锚点日晚于今天 SHALL 返回 422 并提示不可生成未来报告。

#### Scenario: 话术指定日期且无请求 date

- **WHEN** 用户消息为「帮我生成 6 月 10 日的健康报告」且请求未带 `date`
- **THEN** 意图路由抽取 `on_date=2026-06-10`（年份缺省取当前年）并用于任务

#### Scenario: 请求 date 覆盖话术

- **WHEN** 请求 `date=2026-06-12` 且话术提到其他日期
- **THEN** 锚点日为 `2026-06-12`

### Requirement: 数据接入按锚点日取数

系统 SHALL 在 `run_health_assessment` 执行期间，以锚点日 `on_date` 读取健康快照：穿戴/运动取 `date <= on_date` 的最近一条；饮食取 `date = on_date`；基线取 `date < on_date` 历史。`build_report_payload` SHALL 调用 `get_week_overview(user_id, on_date=on_date)`。

#### Scenario: 与 dashboard API 一致

- **WHEN** 锚点日为 D 且 DB 有 seed 数据
- **THEN** 报告 `final_report.chart_data.dashboard` 与 `GET /dashboard/{uid}?date=D` 的 `dashboard` 字段一致（允许非 LLM 字段如 health_advice 差异）

### Requirement: 计划回写使用锚点日

系统 SHALL 在报告成功后将 `user_plans` 写入 `(user_id, plan_date=anchor_date)`，不得固定为今天。

#### Scenario: 历史日报告不写今日计划

- **WHEN** 锚点日为昨天且报告成功
- **THEN** `user_plans` 更新昨天行，今天行不变

### Requirement: 报告缓存按锚点日读取

系统 SHALL 在 `recommendations` 元数据保存 `anchor_date`。`GET /report/latest/{user_id}?date=` SHALL 返回匹配该日的缓存报告；无匹配返回 404。无 `date` 参数时行为与现网一致（最近一次）。

#### Scenario: 按日读取已生成报告

- **WHEN** 用户已为 2026-06-15 生成过报告且再次 `GET /report/latest/1?date=2026-06-15`
- **THEN** 返回该日缓存报告且 `anchor_date=2026-06-15`

### Requirement: Chat 响应回显锚点日

系统 SHALL 在 `intent=report` 的 `ChatResponse` 中返回 `anchor_date` 与 `task_id`。

#### Scenario: 前端校验日期

- **WHEN** chat 返回 `task_id` 与 `anchor_date`
- **THEN** 前端可将其与报告页当前 `date` 比对以决定是否展示健康建议

### Requirement: Plan 端点对齐

系统 SHALL 在 `POST /plan` 请求体接受可选 `date`，语义与 `/chat` 报告分支一致，并写入同一评估任务链路。

#### Scenario: 一键生成指定日报告

- **WHEN** `POST /plan` 带 `user_id=1`、`date=2026-06-18`
- **THEN** 任务锚点日为 2026-06-18

### Requirement: 报告页 Chat 传参

系统 SHALL 在健康报告页使用 ChatDock 发送消息时，附带当前 `useUserStore().userId` 与 `useReportStore().date`。

#### Scenario: 看板切换日期后 chat

- **WHEN** 用户在报告页将日期切至 D 并发送「生成报告」
- **THEN** `POST /chat` 请求含 `date=D` 与当前 user_id

### Requirement: 健康建议与日看板门控

系统 SHALL 仅在缓存报告 `anchor_date` 与报告页当前选中 `date` 一致时，在 `HealthAdviceCard` 展示 LLM 三卡建议；否则展示占位或引导生成文案。

#### Scenario: 切换日期后建议隐藏

- **WHEN** 用户查看看板日期 D2，但最近 LLM 报告锚点日为 D1
- **THEN** 健康建议区不展示 D1 的文案
