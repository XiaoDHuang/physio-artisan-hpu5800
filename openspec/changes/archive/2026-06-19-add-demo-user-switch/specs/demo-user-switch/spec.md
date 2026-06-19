# demo-user-switch Specification

## Purpose

为答辩演示提供前端「演示用户切换」能力，使四页只读 API 与 Chat 报告生成统一使用可切换的 `user_id`（1=小明向好 / 2=小强恶化），与 `seed_week_history_v31.py` 双用户剧情对齐。

## Requirements

### Requirement: 全局演示用户状态

系统 SHALL 提供 Pinia store `useUserStore`，维护当前 `userId`（允许值 `1` | `2`，默认 `1`）及演示用户名称映射（1→小明，2→小强）。

#### Scenario: 默认用户

- **WHEN** 首次打开应用且 localStorage 无记录
- **THEN** `userId=1`，问候语显示「Hello 小明」

#### Scenario: 持久化恢复

- **WHEN** localStorage 存有 `hpu-demo-user-id=2` 且用户刷新页面
- **THEN** `userId=2`，四页取数使用 `/…/2` 路径

### Requirement: Header 切换入口

系统 SHALL 在 `AppHeader` 右侧头像提供点击下拉，列出两名演示用户；选择非当前用户后触发切换。

#### Scenario: 切换到 user=2

- **WHEN** 用户在 Header 下拉选择「小强」
- **THEN** `userId` 变为 2，问候语变为「Hello 小强」，当前用户菜单项标记「（当前）」

#### Scenario: 切换进行中防重复

- **WHEN** 切换触发的四页并行刷新尚未完成
- **THEN** 头像按钮 disabled 并显示 loading 态

### Requirement: 四页取数贯通 userId

系统 SHALL 使 `report`、`exercise`、`sleep`、`nutrition` 四个 Pinia store 的 `load()` 在未显式传入 `userId` 时使用 `useUserStore().userId` 调用对应 `GET /…/{user_id}` API。

#### Scenario: 运动页随用户变化

- **WHEN** 从 user=1 切换到 user=2 后查看 `/exercise`
- **THEN** 页面展示 user=2 的运动数据（与 seed 恶化周一致）

### Requirement: 切换后刷新与清缓存

系统 SHALL 在用户切换后：① 并行调用四页 store 的 `load()`；② 各 store 在 load 开始时清空上一用户缓存数据；③ 重置 chat store 会话状态。

#### Scenario: 不串显上一用户 KPI

- **WHEN** 从 user=1 切换到 user=2
- **THEN** 切换瞬间不继续显示 user=1 的 KPI，加载完成后为 user=2 数据

#### Scenario: Chat 会话重置

- **WHEN** 切换用户
- **THEN** `conversationId` 与最后一轮问答被清空

### Requirement: 报告页 Chat 传递 userId

系统 SHALL 在健康报告页 ChatDock 发送消息时附带当前 `useUserStore().userId`（与 `add-chat-report-by-date` 协同）。

#### Scenario: user=2 生成报告

- **WHEN** 当前为 user=2 且在报告页触发 report 意图
- **THEN** `POST /chat` 请求体含 `user_id=2`
