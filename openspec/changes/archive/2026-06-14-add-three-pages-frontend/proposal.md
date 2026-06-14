## Why

「运动分析 / 睡眠监测 / 饮食管理」三页当前是占位空白（[ExerciseView](frontend/src/views/ExerciseView.vue) 等仅显示"功能建设中"）。变更①（第一层）已规划好三个后端只读端点与稳定契约，本变更（第二层）按该契约把三页真正实现出来，与已上线的「健康报告」页风格、架构一致。

依赖关系：本变更消费变更① 的端点 `GET /sleep|exercise|nutrition/{uid}` 与 `POST /sleep/entry`；契约即稳定缝，第三层后端换源时本前端零改动。

## What Changes

- 抽公共顶部 Header 组件 `components/common/AppHeader.vue`，四页（含健康报告）统一使用：左=页面标题、中=页面自定义槽位（健康报告放时间选择按钮）、右=共用信息簇（当前日期/`Hello 用户名`/头像）；现有 `components/report/ReportHeader.vue` 由其取代，`ReportView` 改用 `AppHeader` 并把原中间 pill/导出按钮移入其槽位。
- 实现三个页面视图，替换现有占位：
  - `SleepView` —— 今日睡眠概况(评分环)/睡眠时长/小憩(进度条+达标)/今日睡眠情况/近7-14天趋势(柱+线)/个性化建议(睡食动 tab + 食物清单)/睡眠时间录入表单。
  - `ExerciseView` —— Banner/今日运动总览(4指标+进度)/今日状态(饮食睡眠疲劳)/今日运动记录/本周运动趋势(柱)/今日运动建议/成就横幅。
  - `NutritionView` —— 日期选择+顶部4卡 KPI/能量摄入概览(环形+宏量条)/今日分餐记录/运动建议/能康助手聊天。
- 新增取数层与状态：`api/` 三页接口函数 + `api/types.ts` 三页类型；`stores/` 三页 store（沿用 `report.ts` 的 load 模式）。
- 新增页面级组件（`components/sleep|exercise|nutrition/`），图表采用 **ECharts**（`echarts` + `vue-echarts`，按需注册 Bar/Line/Pie/Gauge）渲染：评分仪表/能量环形/柱+线双轴趋势/本周柱状等；简单单条进度条可仍用 CSS。
- 睡眠录入表单调用 `POST /sleep/entry`，保存后刷新该页数据。
- 复用现有 `ChatDock` 于饮食/（如设计需要）其它页；多模态按钮(图片/视频)沿用现状占位，不在本期实现上传。
- 三页对 `sources` 字段做轻量"模拟"标注能力（可选小标记），便于演示区分真实/模拟。

> 非目标：不改后端（变更①）、不做表/重刷（变更③）、不实现多模态上传、不做用户登录态（沿用 `USER_ID=1`）。

## Capabilities

### New Capabilities
- `app-header-ui`: 四页共用顶部 Header 组件（左标题 + 中间页面槽 + 右侧当前时间/用户名/头像），取代 `ReportHeader.vue`。
- `sleep-monitoring-ui`: 睡眠监测页前端实现（视图+组件+取数+录入表单），消费 `GET /sleep/{uid}` 与 `POST /sleep/entry`。
- `exercise-analysis-ui`: 运动分析页前端实现（视图+组件+取数），消费 `GET /exercise/{uid}`。
- `nutrition-management-ui`: 饮食管理页前端实现（视图+组件+取数+日期切换+聊天复用），消费 `GET /nutrition/{uid}?date=`。

### Modified Capabilities
<!-- 无：openspec/specs/ 为空；SideNav/router/AppLayout 已存在，本变更仅填充占位视图，不改其需求。 -->

## Impact

- **代码（仅 frontend/src）**：
  - `views/SleepView.vue`、`ExerciseView.vue`、`NutritionView.vue`：占位 → 实现。
  - 新增 `api/sleep.ts`、`api/exercise.ts`、`api/nutrition.ts`（或合并入 `api/pages.ts`）+ `api/types.ts` 三页类型。
  - 新增 `stores/sleep.ts`、`stores/exercise.ts`、`stores/nutrition.ts`。
  - 新增 `components/common/AppHeader.vue`（四页共用顶部 Header）；`views/ReportView.vue` 改用之，`components/report/ReportHeader.vue` 退役删除。
  - 新增 `components/sleep|exercise|nutrition/*.vue`（页面分块卡片与 ECharts 图表）+ `components/common/EChart.vue`（vue-echarts 封装）。
  - 复用：`http.ts`、`ChatDock.vue`、`SectionCard.vue`、`SideNav.vue`、`AppLayout.vue`、`theme.ts`/`style.css` 变量；路由 `meta.title` 作为 Header 标题缺省。
- **依赖**：新增 `echarts` 与 `vue-echarts`（`frontend/package.json`），按需注册图表组件树摇。
- **路由**：已存在 `/exercise`、`/sleep`、`/nutrition`，无需改 router。
- **后端**：仅消费变更① 端点；本变更不改后端。
