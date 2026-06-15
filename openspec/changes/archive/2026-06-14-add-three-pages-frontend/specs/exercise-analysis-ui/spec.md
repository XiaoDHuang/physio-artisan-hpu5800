## ADDED Requirements

### Requirement: 运动分析页渲染
系统 SHALL 在 `/exercise` 路由渲染运动分析页，挂载时通过 store 调用 `GET /exercise/{USER_ID}` 取数；加载中占位，失败提示且不崩溃，空字段显示"—"。

#### Scenario: 进入页面成功取数
- **WHEN** 用户切到 `/exercise` 且后端返回 200
- **THEN** 渲染 Banner、今日运动总览、今日状态、今日运动记录、本周运动趋势、今日运动建议、成就横幅

### Requirement: 今日运动总览与目标进度
系统 SHALL 渲染步数/消耗/时长/强度四指标，每项含目标值与进度条（CSS 进度条即可）。

#### Scenario: 渲染四指标进度
- **WHEN** `today_overview.steps=8500`、`steps_goal=10000`
- **THEN** 步数卡显示 8500 与"目标 10000 步"，进度条按比例填充

### Requirement: 今日状态三行
系统 SHALL 渲染饮食情况、睡眠情况、身体疲劳度三行，各显示等级标签与摘要。

#### Scenario: 渲染疲劳度
- **WHEN** `today_status.fatigue.level="medium"`
- **THEN** 疲劳度行显示"中等"及建议摘要

### Requirement: 今日运动记录与本周趋势（ECharts 柱）
系统 SHALL 列出当日多条运动记录（类型/时间段/时长或距离/消耗），并用 ECharts 柱状渲染本周逐日步数趋势与目标线（markLine）。

#### Scenario: 多条运动记录
- **WHEN** `today_records` 含 3 条
- **THEN** 列表渲染 3 行，每行含类型、时间段、距离或时长、消耗

#### Scenario: 无运动记录
- **WHEN** `today_records` 为空数组
- **THEN** 列表区显示空状态文案，不报错

### Requirement: 今日运动建议与成就
系统 SHALL 渲染运动/饮食/睡眠三段建议与成就横幅（如"超越 N% 用户"）。

#### Scenario: 渲染建议与成就
- **WHEN** 接口返回 `advice` 三段与 `achievement.percentile=72`
- **THEN** 建议区显示三段文本，底部成就横幅显示"超越了 72% 的用户"
