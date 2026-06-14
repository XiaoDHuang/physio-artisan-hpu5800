## ADDED Requirements

### Requirement: 饮食管理页渲染
系统 SHALL 在 `/nutrition` 路由渲染饮食管理页，挂载时通过 store 调用 `GET /nutrition/{USER_ID}?date=` 取数（默认今天）；加载中占位，失败提示且不崩溃，空字段显示"—"。

#### Scenario: 进入页面成功取数
- **WHEN** 用户切到 `/nutrition` 且后端返回 200
- **THEN** 渲染顶部日期+4 卡 KPI、能量摄入概览、今日饮食记录、运动建议、能康助手聊天

### Requirement: 日期切换
系统 SHALL 提供日期前后切换控件，切换时以新 `date` 重新取数并刷新全页。

#### Scenario: 切换到前一天
- **WHEN** 用户点击日期左切换
- **THEN** store 以前一天 `date` 重新调用 `GET /nutrition/{uid}?date=`，各区块刷新

### Requirement: 顶部 KPI 与能量摄入概览
系统 SHALL 渲染每日目标/已摄入/还可摄入/达成率四卡，以及 ECharts 能量环形图与碳水/蛋白质/脂肪宏量条（条可用 CSS），右侧推荐摄入/基础代谢/运动消耗/能量缺口。

#### Scenario: 渲染能量概览
- **WHEN** `energy.total_calories=1800`、`macros` 含三项
- **THEN** 环形中心显示 1800 千卡，三条宏量条按克数/热量/占比渲染

### Requirement: 今日分餐饮食记录
系统 SHALL 按餐别（早/午/晚/加餐）渲染记录，每餐含时间、合计热量与食物明细（名称/克数/单品热量、图标用前端资源）。"记录+"为录入入口（本期可触发 ChatDock 或占位）。

#### Scenario: 渲染分餐记录
- **WHEN** `meals` 含早/午/晚/加餐
- **THEN** 每餐分组渲染其食物明细行

### Requirement: 能康助手聊天复用
系统 SHALL 复用现有单轮 `ChatDock`（`POST /chat`）作为页面底部"能康助手"；多模态（图片识别/视频上传）按钮沿用现状占位，本期不实现上传。

#### Scenario: 发送文本消息
- **WHEN** 用户在能康助手输入文本并发送
- **THEN** 复用 chat store 单轮覆盖式显示最新回复
