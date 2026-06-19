## 1. 后端数据层

- [x] 1.1 `get_week_overview(user_id, days, on_date)`：锚点日窗口、本周/上周划分、锚点日营养
- [x] 1.2 `body_overview.update_date` 回显锚点日；体重/体脂优先锚点日 watch 行

## 2. API

- [x] 2.1 `GET /dashboard/{user_id}?date=` Query 参数与响应顶层 `date`
- [x] 2.2 更新 `docs/接口契约.md` §6.0

## 3. 前端 report store

- [x] 3.1 `getDashboard(userId, date?)` 封装
- [x] 3.2 `report` store：`date`、`prevDay`、`nextDay`、`isToday` getter
- [x] 3.3 `load()` 清空旧 dashboard；优先 dashboard API
- [x] 3.4 `getLatestReport(uid, date)` + `healthAdvice` 锚点日门控

## 4. ReportView UI

- [x] 4.1 Header 动态 `{date}健康数据` 与 `YYYY - MM - DD` 展示
- [x] 4.2 Header 中间槽 `‹ ›` 日期导航（绑定 store.prevDay/nextDay）
- [x] 4.3 移除硬编码 `2026-06-01`
- [x] 4.4 `HealthAdviceCard` 无匹配报告时 emptyHint

## 5. 验证

- [x] 5.1 seed 后默认显示今天日期（非写死 6/1）
- [x] 5.2 14 天内前后切换，KPI/睡眠/运动随日变化
- [x] 5.3 与 `useUserStore.userId` 组合：不同用户同一日数据不同
