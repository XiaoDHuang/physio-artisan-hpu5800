## Why

健康报告页需要按日查看 seed 写入的 **14 天历史曲线**（向好/恶化对照），但原先存在两处问题：

1. **前端 Header 写死** `2026-06-01` 设计稿日期，与 `seed_week_history_v31.py`（`date.today()` 滚动窗口）不一致
2. **后端 `GET /dashboard/{uid}` 无 `date` 参数**，`get_week_overview` 始终取 `watch_data` 最新一行，无法以选定日为「当日」面板并计算相对周对比

饮食页已有 `GET /nutrition/{uid}?date=` + 日期切换，报告看板应对齐同一范式。

## What Changes

- **扩展** `GET /dashboard/{user_id}?date=`：锚点日 `YYYY-MM-DD`，响应增加顶层 `date` 回显
- **扩展** `health_data.get_week_overview(user_id, days, on_date)`：以锚点日为当日面板；周对比 = 锚点前 7 天 vs 再前 7 天；营养取锚点日当天
- **改造** `stores/report.ts`：维护 `date`、`prevDay()` / `nextDay()`（不超过今天）；`load()` 调 `getDashboard(uid, date)`
- **改造** `ReportView`：Header 中间槽 `‹ 日期 ›` 切换；`{date}健康数据` 动态展示；移除硬编码日期
- **改造** 看板取数策略：优先 `/dashboard?date=` 实时 DB 聚合（不再用 `/report/latest` 内嵌的旧 dashboard 覆盖）
- **联动** `/report/latest?date=` 仅拉 LLM 健康建议；`anchor_date !== 当前看板日` 时不展示三卡

## Capabilities

### New Capabilities

- `report-dashboard-by-date`：健康报告页按锚点日查询看板 KPI/身体/睡眠/饮食/运动/周对比

### Modified Capabilities

- `app-header-ui`：健康报告页中间槽由静态 pill 改为可前后切换的日期导航

## Impact

| 层级 | 文件 |
|------|------|
| 后端 | `health_data.py` — `get_week_overview(on_date)` |
| API | `api_server.py` — `GET /dashboard/{uid}?date=` |
| 前端 | `api/report.ts`、`stores/report.ts`、`views/ReportView.vue` |
| 文档 | `docs/接口契约.md` §6.0 |

## 与 `add-chat-report-by-date` 的关系

| 变更 | 职责 |
|------|------|
| **本变更** | 只读看板：切换日期 → 刷新 KPI 等 DB 聚合面板 |
| `add-chat-report-by-date` | 写路径：Chat/Plan 按同一 `date` 触发 LLM 报告生成 |

报告页 Chat 发送时使用 `reportStore.date` 作为锚点日，两变更在 UI 上共用同一日期状态。

## Out of Scope

- 日历弹窗 / 任意日期输入框（仅前后单日切换）
- 修改 `chart_data` 内 LLM 图表（rs_gauge / trend_dual 等仍用原契约）
- 运动/睡眠/饮食页的日期 UX（饮食页已有独立 date 切换）
