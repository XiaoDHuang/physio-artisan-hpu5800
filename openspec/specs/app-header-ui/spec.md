# app-header-ui Specification

## Purpose
TBD - created by archiving change add-three-pages-frontend. Update Purpose after archive.
## Requirements
### Requirement: 四页统一顶部 Header 组件
系统 SHALL 提供共用组件 `components/common/AppHeader.vue`，供四个内容页（健康报告 / 运动分析 / 睡眠监测 / 饮食管理）的右侧内容栏顶部统一使用。结构分三区：**左**=页面标题；**中**=页面自定义槽位（默认空）；**右**=共用信息簇（当前日期、问候+用户名、用户头像）。现有 `components/report/ReportHeader.vue` 由本组件取代。

#### Scenario: 各页渲染统一 Header
- **WHEN** 进入 `/report`、`/exercise`、`/sleep`、`/nutrition` 任一页
- **THEN** 该页内容栏顶部渲染 `AppHeader`，左侧显示该页标题，右侧显示当前日期、`Hello {用户名}` 与头像

#### Scenario: 标题缺省回退路由 meta
- **WHEN** 使用 `AppHeader` 时未显式传入 `title`
- **THEN** 标题取当前路由的 `meta.title`（路由表已为四页配置 title）

### Requirement: Header 右侧信息簇（当前时间 + 用户）
系统 SHALL 在 `AppHeader` 右侧渲染当前日期（含星期，客户端实时取值）、问候语 `Hello {用户名}` 与头像；本期无用户态，用户名取共享常量（头像用占位图标），后续接入用户态再替换。

#### Scenario: 显示当前日期与用户
- **WHEN** 渲染 `AppHeader`
- **THEN** 右侧显示形如"2026年6月3日 星期三"的当前日期与 `Hello {用户名}` 及头像占位

### Requirement: Header 中间页面自定义槽位
系统 SHALL 让 `AppHeader` 中间区域为具名/默认插槽，由各页按需填充；健康报告页 SHALL 在该槽位渲染其自有的时间选择按钮（及原导出等按钮），其余三页中间槽位默认留空。

#### Scenario: 健康报告页中间时间选择按钮
- **WHEN** 进入 `/report`
- **THEN** `AppHeader` 中间槽位渲染健康报告页自有的时间选择按钮（其余三页中间为空）

#### Scenario: 其余页中间留空
- **WHEN** 进入 `/exercise`、`/sleep` 或 `/nutrition`
- **THEN** `AppHeader` 中间槽位不渲染额外内容，仅保留左标题与右信息簇

