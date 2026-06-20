# report-dashboard-by-date Specification

## Purpose

使健康报告页看板（KPI、身体概览、睡眠/饮食/运动面板、周对比）支持按锚点日 `YYYY-MM-DD` 查询与前后切换，数据来自 `GET /dashboard/{user_id}?date=` 的 DB 实时聚合，与 seed 最近 14 天历史对齐。

## Requirements

### Requirement: Dashboard API 锚点日参数

系统 SHALL 在 `GET /dashboard/{user_id}` 接受可选 Query 参数 `date`（`YYYY-MM-DD`，默认今天），并以该日为锚点聚合看板各面板。

#### Scenario: 指定锚点日查询

- **WHEN** 调用 `GET /dashboard/1?date=2026-06-12`
- **THEN** 返回 200，顶层 `date` 为 `2026-06-12`，且 `dashboard.body_overview.update_date` 为 `2026-06-12`

#### Scenario: 缺省日期

- **WHEN** 调用 `GET /dashboard/1` 无 `date` 参数
- **THEN** 锚点日为今天，顶层 `date` 回显今天

### Requirement: 锚点日周对比语义

系统 SHALL 以锚点日 D 的 `watch_data` 行为「当日」面板；本周统计为 `[D-6, D]`；上周统计为 `[D-13, D-7]`；营养取 `nutrition_logs.date = D`。

#### Scenario: 历史日 KPI 与当日行一致

- **WHEN** seed 在 D 日有完整 watch/nutrition 行且调用 `GET /dashboard/{uid}?date=D`
- **THEN** `dashboard.exercise_today` 与 `dashboard.sleep` 反映 D 日数据而非最新一天

### Requirement: 报告页日期状态与切换

系统 SHALL 在 `useReportStore` 维护当前看板锚点日 `date`；提供 `prevDay()` 与 `nextDay()`；`nextDay()` SHALL 不允许超过今天。

#### Scenario: 切换到前一天

- **WHEN** 用户在报告页点击 Header `‹`
- **THEN** store 以 `date-1` 调用 `load()` 并刷新全页看板

#### Scenario: 今天不能再往后

- **WHEN** 当前 `date` 为今天
- **THEN** Header `›` 按钮 disabled

### Requirement: Header 日期展示与数据一致

系统 SHALL 在报告页 `AppHeader` 中间槽显示可切换日期导航，并展示 `{date}健康数据` 标签；日期文本 SHALL 来自 store/API 回显，不得硬编码固定日期。

#### Scenario: 动态日期 pill

- **WHEN** 当前看板 `date=2026-06-18`
- **THEN** Header 显示 `2026-06-18健康数据` 与格式化日期 `2026 - 06 - 18`

### Requirement: 看板与 LLM 建议分离取数

系统 SHALL 使 KPI/身体/睡眠/饮食/运动/周对比仅来自 `GET /dashboard?date=`；`GET /report/latest?date=` 仅用于 LLM 健康建议三卡。

#### Scenario: 历史日无 LLM 报告

- **WHEN** 选中某日 D 且 `/report/latest?date=D` 返回 404
- **THEN** 看板仍展示 D 日 DB 数据；健康建议区显示引导生成文案而非错误

#### Scenario: 建议与看板日不一致时不展示

- **WHEN** 缓存报告 `anchor_date` 与当前看板 `date` 不同
- **THEN** `healthAdvice` getter 返回 null

### Requirement: 加载态与清缓存

系统 SHALL 在 `load()` 开始时清空旧 `dashboard`；日期切换请求进行中 SHALL 禁用 Header 日期导航按钮。

#### Scenario: 切换日不串显旧 KPI

- **WHEN** 从 D1 切换到 D2 且请求未完成
- **THEN** 不继续显示 D1 的 KPI 数值（dashboard 已置 null）
