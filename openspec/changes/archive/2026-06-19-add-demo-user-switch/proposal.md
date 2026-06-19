## Why

答辩演示需要对比 **user=1 小明（向好周）** 与 **user=2 小强（恶化对照）** 的数据曲线（`seed_week_history_v31.py` 已写入 DB），但前端原先各 Pinia store 写死 `USER_ID = 1`，Header 用户名也是设计稿占位「Kevin」，无法在 UI 上切换用户查看不同剧情。

## What Changes

- **新建** 集中式 `stores/user.ts`：演示用户列表、`userId` 状态、`switchUser()`、`reloadAllStores()`
- **改造** `AppHeader.vue`：头像下拉切换 user=1/2，问候语动态显示「小明/小强」，切换中 loading 禁用
- **改造** 四页数据 store（report / exercise / sleep / nutrition）：`load()` 默认从 `useUserStore().userId` 取数，移除各文件内重复的 `USER_ID = 1`
- **联动** 切换用户时：清空 chat 会话、并行刷新四页 API 缓存；报告页 Chat 传 `user_id`（与 `add-chat-report-by-date` 衔接）
- **持久化** `localStorage` 记住上次选中用户（刷新后保持）

## Capabilities

### New Capabilities

- `demo-user-switch`：Header 演示用户切换 + 全局 userId 贯通四页只读 API

### Modified Capabilities

- `app-header-ui`：右侧信息簇由静态占位改为可切换演示用户

## Impact

| 文件 | 操作 |
|------|------|
| `frontend/src/stores/user.ts` | 新建 |
| `frontend/src/components/common/AppHeader.vue` | 用户下拉 + loading |
| `frontend/src/stores/{report,exercise,sleep,nutrition}.ts` | 读 `useUserStore().userId` |
| `frontend/src/views/ReportView.vue` | Chat 传 `userId`；切换时清报告预览 |
| `frontend/src/stores/chat.ts` | `reset()` 在切换时被调用 |

后端无 DDL；各只读 API 本身已支持 `/…/{user_id}` 路径参数。

## Out of Scope

- 真实登录 / 注册 / 权限体系
- 第三及以上演示用户
- 后端 `/chat` 以外接口的 user 校验（演示环境信任前端传参）
