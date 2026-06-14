# sleep-monitoring-api Specification

## Purpose
TBD - created by archiving change add-three-page-read-apis. Update Purpose after archive.
## Requirements
### Requirement: 睡眠监测页只读聚合端点
系统 SHALL 提供 `GET /sleep/{user_id}` 端点，纯数据库 + mock 聚合（不触发多智能体工作流），一次性返回睡眠监测页所需的全部结构化数据，毫秒级返回。响应顶层 SHALL 包含 `user_id`、`sleep`（页面数据对象）、`sources`（逐字段来源标注）。

#### Scenario: 存在睡眠历史数据
- **WHEN** 调用 `GET /sleep/1` 且 `watch_data` 存在该用户记录
- **THEN** 返回 200，`sleep.today` 含 `sleep_score`、`grade`(由分值派生)、`total_hours`、`deep_sleep_hours`(由 `deep_sleep_percent`×`total_hours` 派生)、`nap_minutes`、`bedtime`、`wake_time`
- **AND** `sources` 中 `sleep_score`/`total_hours` 标为 `db`，派生项标为 `derived`

#### Scenario: 无睡眠历史数据
- **WHEN** 调用 `GET /sleep/{uid}` 且该用户在 `watch_data` 无任何记录
- **THEN** 返回 200，各字段回退 mock 场景值，对应 `sources` 标为 `mock`，端点不报错

### Requirement: 今日睡眠时间与小憩达标判定
系统 SHALL 在响应中给出今日睡眠时长与小憩时长的推荐区间与达标状态。睡眠推荐区间默认 7–9 小时，小憩推荐区间默认 20–30 分钟；区间值取自 `users.goals`，缺省则用上述常量。

#### Scenario: 睡眠时长在推荐区间内
- **WHEN** 今日 `total_hours` 落在睡眠推荐区间内
- **THEN** `sleep.duration.status` 为"达标"，并返回 `recommend_min`/`recommend_max` 区间端点供前端绘制进度条

#### Scenario: 小憩时长超出推荐上限
- **WHEN** 今日 `nap_minutes` 超过小憩推荐上限
- **THEN** `sleep.nap.status` 返回非"适中"的对应等级，并带推荐区间

### Requirement: 近 N 天睡眠趋势
系统 SHALL 通过查询参数 `range`（默认 `7d`，可选 `14d`）返回近 N 天逐日的睡眠时长与睡眠评分序列，供前端绘制柱+线双轴趋势图。

#### Scenario: 默认 7 天趋势
- **WHEN** 调用 `GET /sleep/{uid}`（不带 range）
- **THEN** `sleep.trend` 返回最多 7 个数据点，每点含 `date`、`total_hours`、`sleep_score`，按日期升序

#### Scenario: 指定 14 天趋势
- **WHEN** 调用 `GET /sleep/{uid}?range=14d`
- **THEN** `sleep.trend` 返回最多 14 个数据点

### Requirement: 睡眠页个性化建议
系统 SHALL 返回睡眠/饮食/运动三类个性化建议文本，以及"推荐食物""避免食物"清单。第三层换源后：建议文本优先取自 `user_plans.sleep_plan.suggestions` / `training_plan.reason`（无计划则规则派生，标 `derived`）；食物清单改为对齐前端图标集的 curated 常量（香蕉/燕麦/鸡蛋/牛奶/坚果·咖啡/辛辣食物/油炸食品/甜点/奶茶），标 `default`。结构对前端稳定不变。

#### Scenario: 建议来自计划表、食物来自配置
- **WHEN** 调用 `GET /sleep/{uid}` 且当日 `user_plans` 存在
- **THEN** `sleep.advice` 三段取自计划（`sources` 标 `db`/`derived`），`sleep.foods.recommended/avoid` 为对齐图标集的清单（`sources` 标 `default`）

#### Scenario: 无计划时规则兜底
- **WHEN** 当日无 `user_plans`
- **THEN** `sleep.advice` 由规则派生（`sources` 标 `derived`），不返回硬编码 mock 文案

### Requirement: 睡眠时间手动录入
系统 SHALL 提供 `POST /sleep/entry`，接收入睡时间、起床时间、可选小憩时长，以 `sleep_log` 表为真值源按 `(user_id, sleep_date)` upsert（约束 `wake_time_at > bedtime_at`），并回灌 `watch_data`（`actual_bedtime`/`actual_wake_time`/`nap_min` 列 + `sleep_data` JSONB 镜像 `total_hours`），保持 `GET /sleep` 读取兼容。`total_hours` 由时间差派生。

#### Scenario: 录入写 sleep_log 并回灌
- **WHEN** `POST /sleep/entry` 提交 `bedtime=2026-06-01T23:20`、`wake_time=2026-06-02T07:20`
- **THEN** 返回 200 且 `saved=true`，`sleep_log` 落一行，`watch_data` 对应日期回灌入睡/起床与 `total_hours≈8.0`

#### Scenario: 缺失或非法时间
- **WHEN** `POST /sleep/entry` 未提供 `bedtime`/`wake_time` 或时间非法（起床早于入睡）
- **THEN** 返回 4xx 校验错误且不写库

