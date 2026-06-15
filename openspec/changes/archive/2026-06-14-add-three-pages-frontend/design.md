## Context

「健康报告」页已用一套清晰范式实现：`api/http.ts`(getJson/postJson) → `api/report.ts` → `stores/report.ts`(load + getters) → `views/ReportView.vue` → `components/report/*.vue`。现有报告页图表为 CSS/SVG 手绘（如 `SleepCard` 用 `conic-gradient` 环），尚无第三方图表库；本变更三页改用 **ECharts** 统一渲染图表。栈：Vue3+TS+Pinia+vue-router+ant-design-vue(+ant-design-x-vue)。路由 `/exercise /sleep /nutrition` 已存在并指向占位视图。`ChatDock`(单轮覆盖问答) 与 `SectionCard`(卡片壳) 可直接复用。

本变更按变更① 的契约把三页占位实现为真实页面。

## Goals / Non-Goals

**Goals:**
- 三页与报告页同构（api→store→view→components），仅认变更① 契约字段。
- 图表用 ECharts 统一渲染（按需注册、树摇）；空值/失败优雅降级。
- 睡眠录入闭环（表单→`POST /sleep/entry`→刷新）。

**Non-Goals:**
- 不改后端、不碰表/重刷（变更①③）。
- 不实现多模态上传；不做登录态（`USER_ID=1`）；不改造报告页既有手绘图（仅新三页用 ECharts）。

## Decisions

### D1. 沿用报告页四层范式，每页独立 store
- 每页一个 `api/<page>.ts` + `stores/<page>.ts`（`state{data,loading,error}` + `load(date?/range?)` + getters），`views/<Page>View.vue` `onMounted` 调 `load()`，分块 `components/<page>/*.vue`。
- 备选：合并到 `report.ts`。否决——各页数据形状差异大，分离更清晰、互不影响。

### D2. 图表用 ECharts（`echarts` + `vue-echarts`）
- 选型：`echarts` + `vue-echarts`（Vue3 官方封装的 `<v-chart>` 组件），**按需注册**所需 chart/component（`BarChart`/`LineChart`/`PieChart`/`GaugeChart` + `GridComponent`/`TooltipComponent`/`LegendComponent` 等）并用 `CanvasRenderer`，靠树摇控制体积。
- 用法约定：封装一个轻量 `EChart.vue`（包 `<v-chart :option=...>`，统一主题色取自 `theme.ts`/CSS 变量、`autoresize`），各图表组件只产出 `option`。
- 各图映射：睡眠评分=Gauge/环形 Pie；能量摄入=环形 Pie(+中心总量)；睡眠趋势=Bar+Line 双 yAxis；本周运动趋势=Bar(+目标 markLine)；宏量/目标进度等简单单条进度可仍用 CSS（不必都上 ECharts）。
- 理由：用户指定；双轴趋势/仪表盘/环形用 ECharts 更省事、交互(tooltip/legend)开箱即用、答辩观感更好。
- 备选：CSS/SVG 手绘（与报告页一致、零依赖）。否决——按用户要求改用 ECharts。报告页既有手绘图本期不动，避免无谓回归。

### D3. 类型与 `sources` 标注
- `api/types.ts` 增三页响应类型（含 `sources` 映射）。组件可选地按 `sources[field]==='mock'` 加一个小"模拟"角标，便于演示区分真实/模拟（轻量、可后置）。

### D4. 组件复用与拆分
- 复用：`SectionCard`(卡片壳)、`ChatDock`(饮食页能康助手)、`SideNav/AppLayout/theme`。
- 新增 `components/common/EChart.vue`（`vue-echarts` 薄封装，统一主题 + autoresize），三页图表组件复用。
- 新增分块（示例）：
  - sleep: `SleepScoreCard`(ECharts Gauge/Pie)/`SleepDurationCard`/`SleepDetailCard`/`SleepTrendChart`(ECharts Bar+Line)/`SleepAdviceTabs`/`SleepEntryForm`。
  - exercise: `ExerciseBanner`/`TodayOverviewCard`/`TodayStatusCard`/`TodayRecordsCard`/`WeekTrendChart`(ECharts Bar+markLine)/`ExerciseAdviceCard`/`AchievementBanner`。
  - nutrition: `NutritionKpiCards`/`EnergyOverviewCard`(ECharts 环形 Pie + 宏量条)/`MealRecordsCard`/`ExerciseAdvicePanel` + 复用 `ChatDock`。

### D5. 睡眠录入交互
- `SleepEntryForm` 用 antd DatePicker/TimePicker（已有 antd），保存调 `postJson('/sleep/entry', ...)`，成功后 `store.load()` 刷新；前端先做必填校验再发请求。

### D6. 饮食页日期与聊天
- 日期切换驱动 `store.load(date)`；默认今天。
- 能康助手直接挂 `ChatDock`；多模态按钮保留为占位（不接上传），与当前一致。

### D7. 抽公共顶部 Header（`components/common/AppHeader.vue`）
- **组件 API**：
  - prop `title?: string` —— 左侧标题；缺省回退 `useRoute().meta.title`（路由表四页均已配 title）。
  - 默认插槽（中间区）—— 页面自定义内容；健康报告页填入"时间选择按钮"（+原导出等），其余三页留空。
  - 右侧信息簇（组件内置、四页共用）—— 当前日期+星期（客户端实时）、`Hello {用户名}`、头像占位(SVG)。用户名取共享常量(本期 `Kevin`，无用户态)，预留后续接用户/profile。
- **放置方式**：在每个 View 顶部渲染 `<AppHeader :title="..."/>`（与现有 ReportView 内嵌 header 的模式一致），不下沉到 `AppLayout`——因中间槽位是页面级内容，逐页提供更简单。Header 固定在内容区顶部、其下为可滚动主体。
- **复用迁移**：`ReportView` 用 `AppHeader` 取代 `ReportHeader.vue`，把原中间 pill/导出按钮移进默认插槽；`ReportHeader.vue` 退役删除（右侧日期/问候/头像逻辑迁入 `AppHeader`）。
- 备选：把 Header 放进 `AppLayout` 由 route.meta 驱动。否决——中间槽位页面差异大，layout 级单一 header 需 teleport/具名槽，复杂度更高。

## Risks / Trade-offs
- [ECharts 全量引入体积大] → 用 `echarts/core` 按需注册所需 chart/component + `CanvasRenderer`，树摇控制体积；统一经 `EChart.vue` 复用。
- [ECharts 与 antd/Vite8 集成与按需注册写法成本] → 用 `vue-echarts` 官方封装，集中在 `EChart.vue` 一处注册，组件只传 `option`。
- [mock 字段较多，演示易被误认为真实] → 按 D3 可选角标 + 文案说明；契约已标 `sources`。
- [设计图与 seed 目标值不一致(步数 10000 vs 8000 等)] → 前端只展示接口返回值，差异由变更①/③ 后端统一，前端不写死。
- [antd 时间控件样式与设计图差异] → 以功能为先，样式微调对齐主题变量。

## Migration Plan
- 纯前端新增/替换占位视图，向后兼容；路由不变。无数据迁移。
- 回滚：恢复占位视图即可。

## Open Questions
1. `sources` "模拟"角标本期是否要做？（倾向做一个极轻量可开关的角标，不做也不影响主流程。）
2. 饮食"记录+"与睡眠录入之外，运动页是否需要录入入口？（设计图未显式要求，本期不做，统一走 `/chat` 录入。）
3. 趋势图 hover tooltip：改用 ECharts 后 tooltip 开箱即用，本期默认开启。

## 实现纪要（已落地，由 Claude 实现）

- **公共件**：`components/common/AppHeader.vue`（四页统一，含 subtitle；报告页中间槽放健康数据/日期/导出，`ReportHeader.vue` 已删）、`components/common/EChart.vue`（vue-echarts 封装，集中按需注册 Bar/Line/Pie/Gauge）。装了 `echarts`+`vue-echarts`。
- **每页**：`api/<page>.ts` + `stores/<page>.ts`(load + getters) + `views/<Page>View.vue` + `components/<page>/*`。固定 `USER_ID=1`。图标按 `assets/page-*/中文名` 接入。
- **图表映射**：睡眠评分=Gauge、睡眠趋势=Bar+Line 双轴、能量/饮食=环形 Pie、本周步数=Bar+markLine；简单进度条用 CSS。报告页 SleepCard/NutritionCard 也已改 ECharts。
- **录入闭环**：睡眠页 `SleepEntryForm`(antd 日期/时间) → `POST /sleep/entry` → 成功后 `store.load()` 回刷。
- **聊天复用**：饮食页 `NutritionChatDock` 复用 `useChatStore`（与报告页 `ChatDock` 同一单轮覆盖逻辑），多模态按钮占位未接上传。
- **布局**：`.scroll-area{overflow:auto}` + 内容包裹层 `min-width:1120px`——可用区 <1120 出现横向滚动、内容不压缩；网格列 `min-width:0` 让 >1120 时 ECharts 正常 autoresize。
- **已知（前端如实渲染，归第三层后端处理）**：部分 mock 食物/动作名与图标集不符 → 前端首字占位兜底；详见变更① design.md 的"第三层换源清单"。
