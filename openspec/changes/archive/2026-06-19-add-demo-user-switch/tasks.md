## 1. 用户状态层

- [x] 1.1 新建 `frontend/src/stores/user.ts`：`DEMO_USERS`、`userId`、`switchUser`、`reloadAllStores`
- [x] 1.2 `localStorage` 持久化 `hpu-demo-user-id`

## 2. Header UI

- [x] 2.1 `AppHeader.vue` 头像下拉菜单（小明 / 小强）
- [x] 2.2 问候语绑定 `userName`；切换中 loading 禁用

## 3. 四页 Store 贯通

- [x] 3.1 `report` / `exercise` / `sleep` / `nutrition` store：`load()` 默认 `useUserStore().userId`
- [x] 3.2 移除各 store 内 `USER_ID = 1` 常量
- [x] 3.3 `load()` 开始时清空旧缓存，避免串数据

## 4. 联动

- [x] 4.1 切换时 `useChatStore().reset()`
- [x] 4.2 `reloadAllStores()` 并行刷新四页
- [x] 4.3 报告页 Chat / 导出预览随用户切换清理（`reloadVersion` watch）

## 5. 验证

- [x] 5.1 user=1 ↔ user=2 切换后 KPI/趋势明显不同（seed 向好 vs 恶化）
- [x] 5.2 刷新页面仍保持上次选中用户
