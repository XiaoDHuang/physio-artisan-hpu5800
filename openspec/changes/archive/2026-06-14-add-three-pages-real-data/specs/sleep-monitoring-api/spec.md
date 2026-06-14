## MODIFIED Requirements

### Requirement: 睡眠页个性化建议（mock 兜底）
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
