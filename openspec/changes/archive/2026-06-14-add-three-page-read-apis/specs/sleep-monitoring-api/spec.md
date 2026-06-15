## ADDED Requirements

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

### Requirement: 睡眠页个性化建议（mock 兜底）
系统 SHALL 返回睡眠/饮食/运动三类个性化建议文本，以及"推荐食物""避免食物"清单。本期建议文本与食物清单由规则/mock 产出并在 `sources` 标为 `mock`，结构对前端稳定，便于第三层接 LLM/真实数据后无缝替换。

#### Scenario: 返回三类建议与食物清单
- **WHEN** 调用 `GET /sleep/{uid}`
- **THEN** `sleep.advice` 含 `sleep`/`nutrition`/`exercise` 三段文本，`sleep.foods` 含 `recommended`/`avoid` 两个名称清单
- **AND** 上述字段在 `sources` 中标为 `mock`

### Requirement: 睡眠时间手动录入
系统 SHALL 提供 `POST /sleep/entry`，接收用户手动录入的入睡时间、起床时间、可选小憩时长，写入对应日期 `watch_data` 行的 `sleep_data` JSONB（键 `bedtime`/`wake_time`/`nap_minutes`/`total_hours`），不新增表或列；同日已有行则更新该 JSONB，无行则插入。`total_hours` 由入睡/起床时间差派生。

#### Scenario: 录入有效的入睡与起床时间
- **WHEN** `POST /sleep/entry` 提交 `bedtime=2026-06-01T23:20` 与 `wake_time=2026-06-02T07:20`
- **THEN** 返回 200 且 `saved=true`，`watch_data.sleep_data` 写入 `bedtime`/`wake_time`，并派生 `total_hours≈8.0`

#### Scenario: 缺失必填时间字段
- **WHEN** `POST /sleep/entry` 未提供 `bedtime` 或 `wake_time`
- **THEN** 返回 4xx 校验错误且不写库
