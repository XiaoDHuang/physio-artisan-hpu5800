# app-header-ui Specification

## Purpose

四页统一顶部 Header：左标题、中页面自定义槽、右信息簇（日期、问候、演示用户切换）。

## Requirements

### Requirement: 四页统一顶部 Header 组件

系统 SHALL 提供共用组件 `components/common/AppHeader.vue`，供四个内容页（健康报告 / 运动分析 / 睡眠监测 / 饮食管理）的右侧内容栏顶部统一使用。结构分三区：**左**=页面标题；**中**=页面自定义槽位（默认空）；**右**=共用信息簇（当前日期、问候+用户名、用户头像）。

#### Scenario: 各页渲染统一 Header

- **WHEN** 进入 `/report`、`/exercise`、`/sleep`、`/nutrition` 任一页
- **THEN** 该页内容栏顶部渲染 `AppHeader`，左侧显示该页标题，右侧显示当前日期、`Hello {用户名}` 与头像

#### Scenario: 标题缺省回退路由 meta

- **WHEN** 使用 `AppHeader` 时未显式传入 `title`
- **THEN** 标题取当前路由的 `meta.title`（路由表已为四页配置 title）

### Requirement: Header 右侧信息簇（当前时间 + 用户）

系统 SHALL 在 `AppHeader` 右侧渲染当前日期（含星期，客户端实时取值）、问候语 `Hello {用户名}` 与可点击头像。用户名 SHALL 取自 `useUserStore().userName`（演示用户：小明 / 小强）；头像点击 SHALL 弹出演示用户切换菜单（user=1 / user=2），切换后问候语与全局取数 userId 同步更新。

#### Scenario: 显示当前日期与用户

- **WHEN** 渲染 `AppHeader` 且当前 `userId=1`
- **THEN** 右侧显示当前日期与 `Hello 小明` 及可点击头像

#### Scenario: 切换演示用户

- **WHEN** 用户从头像菜单选择「小强」
- **THEN** 问候语变为 `Hello 小强`，且四页数据按 user=2 刷新

#### Scenario: 切换加载态

- **WHEN** 用户切换触发数据刷新
- **THEN** 头像按钮处于 disabled/loading 直至刷新完成

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
