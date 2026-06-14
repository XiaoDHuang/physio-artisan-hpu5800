## ADDED Requirements

### Requirement: 睡眠监测页渲染
系统 SHALL 在 `/sleep` 路由渲染睡眠监测页，挂载时通过 store 调用 `GET /sleep/{USER_ID}` 取数并渲染各分块；加载中显示骨架/占位，失败显示错误且不崩溃；字段为空显示"—"。

#### Scenario: 进入页面成功取数
- **WHEN** 用户切到 `/sleep` 且后端返回 200
- **THEN** 页面渲染今日概况、睡眠时长、小憩、今日睡眠情况、趋势、个性化建议、录入表单各区块

#### Scenario: 取数失败
- **WHEN** 后端返回非 2xx 或网络失败
- **THEN** 页面显示错误提示，不抛未捕获异常，其余静态结构仍可见

### Requirement: 今日睡眠概况与达标可视化
系统 SHALL 用 ECharts 渲染睡眠评分仪表/环形图，并显示等级文案与概况文本；睡眠时长与小憩 SHALL 以进度条呈现推荐区间与达标徽标。

#### Scenario: 渲染评分环与达标
- **WHEN** `sleep.today.sleep_score=85`、`duration.status="达标"`
- **THEN** 环显示 85 与等级，睡眠时长区块显示"达标"徽标及 7-9h 区间进度

### Requirement: 近 N 天睡眠趋势图（ECharts 柱+线双轴）
系统 SHALL 用 ECharts 渲染近 7/14 天的睡眠时长柱状与睡眠评分折线双轴图，并提供 7天/14天 切换；切换时按 `range` 重新取数。

#### Scenario: 切换 14 天
- **WHEN** 用户在趋势区选择"近14天"
- **THEN** store 以 `range=14d` 重新取数，趋势图重绘为最多 14 个柱+点

### Requirement: 睡眠时间录入表单
系统 SHALL 提供入睡时间、起床时间（及可选小憩）录入表单，点击保存调用 `POST /sleep/entry`；成功后刷新本页数据并给出成功反馈，必填缺失时阻止提交并提示。

#### Scenario: 保存录入成功
- **WHEN** 用户填入睡/起床时间并点击"保存记录"，后端返回 `saved=true`
- **THEN** 显示成功提示并重新拉取 `GET /sleep/{uid}`，今日睡眠情况随之更新

#### Scenario: 必填缺失
- **WHEN** 用户未填入睡或起床时间即点击保存
- **THEN** 前端阻止提交并提示必填，不发请求

### Requirement: 个性化建议与食物清单
系统 SHALL 渲染"睡眠/饮食/运动"分页签建议文本与"推荐食物/避免食物"清单（图标用前端资源，名称来自接口）。

#### Scenario: 切换建议页签
- **WHEN** 用户点击"饮食"页签
- **THEN** 显示 `advice.nutrition` 文本与推荐/避免食物清单
