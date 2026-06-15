# 实施任务（第二层·前端三页实现）

> 实际由 **Claude 直接实现**（用户指示，非 deepseek）。约束遵守：仅 `frontend/src`(+package.json 装 echarts)，只认变更① 契约；不改后端、不碰表、不做多模态上传。
> 范式：`api/*.ts → stores/*.ts → views → components`，图表用 ECharts（`echarts`+`vue-echarts`，按需注册树摇），复用 `SectionCard`/`ChatDock`/`SideNav`/`theme`。
> 实现期间用户追加：①健康报告页图表也改 ECharts；②全站内容区下限 `min-width:1120px` + 横向滚动（不无限压缩）。

## 0. 图表基建（ECharts）

- [x] 0.1 安装依赖：`echarts` + `vue-echarts`
- [x] 0.2 `components/common/EChart.vue`：vue-echarts 薄封装，按需注册 Bar/Line/Pie/Gauge + Grid/Tooltip/Legend/MarkLine + CanvasRenderer，autoresize；组件只产出 option

## 1. 公共 Header（AppHeader，四页统一）

- [x] 1.1 `components/common/AppHeader.vue`：左 title(缺省回退 `route.meta.title`) + 可选 subtitle、中默认插槽、右当前日期+`Hello {用户名}`+头像
- [x] 1.2 `ReportView.vue` 改用 `AppHeader`（中间槽放"健康数据/日期/导出报告"）；**删除 `ReportHeader.vue`**；报告页无回归

## 2. 取数层与类型

- [x] 2.1 `api/types.ts` 增 Exercise/Sleep/Nutrition 响应类型（含各分块字段与 `sources` 映射、SourceMap）
- [x] 2.2 `api/exercise.ts`/`api/sleep.ts`(getSleep+postSleepEntry)/`api/nutrition.ts`，复用 `http.ts`
- [x] 2.3 `stores/exercise.ts`/`stores/sleep.ts`(load(range)+saveEntry)/`stores/nutrition.ts`(load(date)+prevDay/nextDay)，沿用 `report.ts` 模式，USER_ID=1

## 3. 睡眠监测页（spec: sleep-monitoring-ui）

- [x] 3.1 `SleepView.vue`：AppHeader + onMounted load + 两栏布局
- [x] 3.2 `SleepScoreCard`(ECharts Gauge 环形评分 + banner-bg 睡觉插画 + 文案)、`RangeBarCard`(达标进度条，睡眠/小憩复用)
- [x] 3.3 `SleepDetailCard`(入睡/起床/时长/深睡)、`SleepTrendChart`(ECharts 柱+线双轴，7/14天 a-select 切换→按 range 重取)
- [x] 3.4 `SleepAdviceTabs`(睡/食/动页签 + 推荐/避免食物，食物名→图标映射+首字占位兜底)
- [x] 3.5 `SleepEntryForm`(antd 日期/时间，必填校验→`postSleepEntry`→成功后 load 刷新 + message 反馈)

## 4. 运动分析页（spec: exercise-analysis-ui）

- [x] 4.1 `ExerciseView.vue`：AppHeader + onMounted load + 两栏布局
- [x] 4.2 `ExerciseBanner`(banner-bg 整图)、`TodayOverviewCard`(步数/消耗/时长/强度 + CSS 进度条)
- [x] 4.3 `TodayStatusCard`(饮食/睡眠/疲劳度三行)、`TodayRecordsCard`(多条记录，空状态兜底)
- [x] 4.4 `WeekTrendChart`(ECharts 柱 + 目标 markLine)、`ExerciseAdviceCard`(运动/饮食/睡眠三段)、`AchievementBanner`(超越N%)

## 5. 饮食管理页（spec: nutrition-management-ui）

- [x] 5.1 `NutritionView.vue`：AppHeader + onMounted load + 日期切换驱动 load(date)
- [x] 5.2 `NutritionKpiBar`(日期切换 + 每日目标/已摄入/还可摄入/达成率四卡)
- [x] 5.3 `EnergyOverviewCard`(ECharts 能量环形 + 碳水/蛋白/脂肪宏量条 CSS + 右侧推荐/BMR/运动消耗/能量缺口 + 温馨提示)
- [x] 5.4 `MealRecordsCard`(早/午/晚/加餐 + 食物明细，食物名→图标兜底)、`ExerciseAdvicePanel`(类型/时长/消耗 + 动作组次)
- [x] 5.5 `NutritionChatDock` 作"能康助手"：**复用 `useChatStore`** 单轮交互，按饮食页样式；多模态按钮占位

## 6. 健康报告页图表改 ECharts（用户追加）

- [x] 6.1 `SleepCard` 改 ECharts：Gauge 评分环 + 浅睡/深睡分时堆叠柱
- [x] 6.2 `NutritionCard` 改 ECharts：宏量环形 Pie + 右侧图例（均衡度条保留 CSS）

## 7. 布局与一致性（用户追加 1120 下限）

- [x] 7.1 四页内容包裹层 `min-width:1120px` + `.scroll-area{overflow:auto}`：低于 1120 横向滚动、不压缩
- [x] 7.2 失败/加载/空值降级：错误提示、空字段"—"，不崩溃
- [x] 7.3 `vue-tsc` + `vite build` 通过；四页路由切换/高亮正常；预览逐页核对设计图、睡眠录入闭环、饮食日期切换
- [ ] 7.4 （可选，未实现）按 `sources[field]==='mock'` 渲染"模拟"角标——延后，非阻塞
