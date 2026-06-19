# app-header-ui Delta

## MODIFIED Requirements

### Requirement: Header 中间页面自定义槽位

系统 SHALL 让 `AppHeader` 中间区域为具名/默认插槽，由各页按需填充。健康报告页 SHALL 在该槽位渲染：**(1)** 当前锚点日数据标签 `{date}健康数据`；**(2)** 日期前后切换控件（`‹` / 格式化日期 / `›`），切换后重新加载看板；**(3)** 导出报告等页面自有按钮。其余三页中间槽位默认留空。

#### Scenario: 健康报告页日期切换

- **WHEN** 进入 `/report` 且用户点击 Header 日期导航 `‹`
- **THEN** 看板数据按前一天锚点日刷新，Header 日期文案同步更新

#### Scenario: 健康报告页显示锚点日标签

- **WHEN** 当前看板锚点日为 `2026-06-10`
- **THEN** Header 中间槽显示 `2026-06-10健康数据` 与对应格式化日期

#### Scenario: 其余页中间留空

- **WHEN** 进入 `/exercise`、`/sleep` 或 `/nutrition`
- **THEN** `AppHeader` 中间槽不渲染报告页日期导航，仅保留左标题与右信息簇
