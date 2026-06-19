# app-header-ui Delta

## MODIFIED Requirements

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
