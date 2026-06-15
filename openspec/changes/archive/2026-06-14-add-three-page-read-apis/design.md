## Context

「健康报告」页已落地：后端 `GET /dashboard/{uid}`（`health_data.get_week_overview`，纯 DB 聚合）+ `GET /report/latest/{uid}`（落库报告缓存），前端 `ReportView` + `stores/report.ts` 取数渲染。本变更为「运动分析 / 睡眠监测 / 饮食管理」三页复制同一套范式做后端取数层。

现状约束：
- 现有表：`watch_data`（日级穿戴，含 `hrv_data`/`sleep_data` JSONB）、`exercise_records`（`analysis_result` JSONB）、`nutrition_logs`（`nutrition_result`/`recognized_foods` JSONB、`balance_score`）、`users`（含 `body_fat_pct`/`muscle_mass_kg`/`goals` JSONB）。
- `health_data.py` 已有：`_query_one/_query_all/_avg`、`get_user_profile`、`get_health_snapshot`、`compute_metrics`（RS/HRR/TRIMP/BMI/BMR/TDEE/body_age/fatigue）、`get_week_overview`。
- `seed_week_history.py` 造了最近 14 天数据（user=1 向好、user=2 恶化），`sleep_data` 已含 `stages_timeline`。
- 表结构定稿由另一同学进行中，故本期**不改表**，缺字段后端 mock 兜底，留待第三层换源。

## Goals / Non-Goals

**Goals:**
- 三个只读端点 + 一个睡眠录入端点，契约稳定、毫秒级、复用 `health_data.py`。
- 每字段标注 `db | mock | derived` 来源，mock 集中在聚合层、不污染契约。
- 同步 `docs/接口契约.md`。

**Non-Goals:**
- 不实现前端（第二层另起变更 `*-frontend`）。
- 不做表结构设计/迁移/重刷历史（第三层另起变更）。
- 不接真实视觉/LLM 生成；不改 `/chat`、`/dashboard`、`/report/latest`。

## Decisions

### D1. 端点形态：每页一个只读 GET，镜像 `/dashboard/{uid}`
- 路由薄、聚合在 `health_data.py`：新增 `get_sleep_overview(uid, range_days)`、`get_exercise_overview(uid)`、`get_nutrition_overview(uid, date)` 与 `save_sleep_entry(...)`。
- 备选：合并为一个 `/page/{name}/{uid}`。否决——三页字段差异大、前端 store 分离，独立端点更清晰且与 `/dashboard` 一致。

### D2. 来源标注：响应内 `sources` 字典
- 复用既有 `data_sources` 语义（`db`/`mock`/`derived`，`derived`=由公式/`health_tools` 算出）。前端可据此标"真实/模拟"。第三层换源时只需把对应字段 `mock→db` 并删 mock 分支。

### D3. mock 集中在聚合层、按"缺口类型"归类
- **结构缺口**（表能扩、第三层补）：饮食分餐单品明细(name/grams/calories)、运动记录的 `time_range`/`distance_km`、跨用户成就 `percentile`。
- **agent 产出缺口**（与报告 `cards.training`/`health_advice` 同源，后续接 LLM）：训练方案组次、三类个性化建议文本、睡眠/饮食食物推荐清单。
- mock 值贴近设计图与 seed 风格，保证演示自然。

### D4. 睡眠录入零建表：写 `watch_data.sleep_data` JSONB
- `POST /sleep/entry` 把 `bedtime`/`wake_time`/`nap_minutes`/派生 `total_hours` upsert 进对应日期行的 `sleep_data`（JSONB 可加任意键，无需 DDL）。同日有行则合并更新，无行则插入最小行。
- 备选：新增 `sleep_entries` 表。否决——属第三层表设计范畴，本期不碰表。

### D5. 复用既有派生，避免逻辑漂移
- 睡眠等级/达标、达成率、能量缺口等就地按简单规则派生；疲劳度直接调 `compute_metrics(...)['derived']['fatigue']`；BMR/BMI 调 `health_tools`。不重复造轮子。

## 字段来源映射（实现据此填充 `sources`）

### `GET /sleep/{uid}`
| 字段 | 来源 | 说明 |
|---|---|---|
| today.sleep_score / total_hours | db | `watch_data.sleep_data` |
| today.grade / deep_sleep_hours / duration.status / nap.status | derived | 分值/区间派生 |
| today.nap_minutes / bedtime / wake_time | db→mock | 有录入则 db(`sleep_data`)，否则 mock |
| duration/nap.recommend_min/max | db→默认 | `users.goals`，缺省常量(7-9h / 20-30m) |
| trend[].total_hours / sleep_score | db | 近 7/14 天 `watch_data` |
| advice.{sleep,nutrition,exercise} / foods.{recommended,avoid} | mock | 规则/静态清单 |

### `GET /exercise/{uid}`
| 字段 | 来源 | 说明 |
|---|---|---|
| today_overview.steps/calories_burned/duration_minutes | db | `watch_data` |
| today_overview.*_goal | db→默认 | `users.goals` |
| today_overview.intensity | derived | 同 `get_week_overview` 规则 |
| today_status.diet/sleep | db+derived | 当日营养/睡眠 + 等级 |
| today_status.fatigue | derived | `compute_metrics` fatigue |
| today_records[].exercise_type/duration_minutes/calories | db | `exercise_records.analysis_result` |
| today_records[].time_range/distance_km | mock | 表无字段 |
| week_trend[].steps + steps_goal | db | 近 7 天 `watch_data` + goals |
| advice.* / achievement.percentile | mock | 规则/跨用户统计缺口 |

### `GET /nutrition/{uid}?date=`
| 字段 | 来源 | 说明 |
|---|---|---|
| kpi.goal_calories | db | `users.goals.calorie_intake_target` |
| kpi.intake_calories | db | 当日 `nutrition_result.total_calories` |
| kpi.remaining_calories / achievement_rate | derived | |
| energy.total_calories / macros.*.grams,calories | db | `nutrition_result` |
| energy.macros.*.percent / bmr / energy_gap | derived | ratios + `health_tools`；**energy_gap = goal_calories − intake_calories**（按设计图口径，与"还可摄入"同值；可为负=已超目标，不 clamp） |
| energy.exercise_burn | db | `watch_data.calories_burned` |
| energy.recommended_calories | db→默认 | goals |
| meals[].meal_type/time/total_calories | db→mock | seed 仅日级汇总，分餐结构 mock |
| meals[].foods[].name/grams/calories | mock | 结构缺口 |
| exercise_advice.* | mock | agent 产出缺口 |

## Risks / Trade-offs
- [seed 与设计图目标值不一致：seed `steps_goal=8000`/`exercise_minutes_goal=30`，图示 10000/60] → 以 `users.goals` 为准，goals 缺省常量对齐设计图；差异写入契约说明，第三层重刷时统一。
- [seed 写 `nutrition_logs.meal_type='daily'` 单行、无分餐] → 分餐与单品明细本期 mock；契约标注；第三层补结构后换源。
- [`exercise_records` 当前每训练日仅 1 行，设计图示多条会话] → 聚合按多行返回，mock 可补足演示条数；不阻塞契约。
- [mock 与真实混排可能误导] → 强制 `sources` 标注，前端可显式标"模拟"。
- [设计图个别字段疑似笔误（如"深度睡眠 8 小时"、"运动强度 58 分钟"）] → 按合理语义实现（深睡=deep%×总时长；强度=类别），记入 Open Questions 待确认。

## Migration Plan
- 纯新增端点 + 新增聚合函数，向后兼容，无 DDL、无数据迁移。
- 回滚：移除新增路由与函数即可，不影响既有端点。

## Open Questions
1. `users.goals` 是否按设计图更新为 `steps_goal=10000`/`exercise_minutes_goal=60`/`calorie_intake_target=2000`？（属数据/重刷，倾向第三层统一处理，本期 goals 缺省常量对齐设计图。）
2. 睡眠"小憩"是否需要独立录入入口，还是并入 `POST /sleep/entry` 可选字段？（本期并入为可选 `nap_minutes`。）
3. `GET /nutrition` 的 `date` 越界（无数据日）返回空结构还是 404？（本期倾向返回空结构 + mock 兜底，保持页面可渲染。）

## 实现纪要（已落地 + 第三层换源清单）

后端三端点 + `POST /sleep/entry` 已实现于 `api_server.py`，聚合于 `health_data.py`（`get_sleep/exercise/nutrition_overview` + `save_sleep_entry` + `_get_goals/_mark/_get_watch_sequence/_execute_write`）。review 修复：goals=NULL 的 500、写失败回滚、"今日"取最新行、录入非法时间→422、`energy_gap = 目标 − 已摄入`。`docs/接口契约.md` §6/§7 已更新。

**第三层（扩表 + 换源）待办清单**（每项：当前 mock/缺口 → 目标真实源）：

| 页/字段 | 当前 | 第三层目标 |
|---|---|---|
| sleep `today.bedtime/wake_time/nap_minutes` | 存 `watch_data.sleep_data` JSONB（录入写入），无录入则 mock | 可正式化为列或保留 JSONB；保证设备/录入两路 |
| sleep `advice.*` | mock 规则 | LLM/agent 或建议表 |
| sleep `foods.recommended/avoid` | mock 静态，名称与图标集不符 | 对齐图标集的 curated 配置/表（香蕉/燕麦/鸡蛋/牛奶/坚果·咖啡/辛辣食物/油炸食品/甜点/奶茶）|
| exercise `today_records.time_range` | mock（`exercise_records` 无起止时间列）| 加列 `start_time/end_time`（或 JSONB）|
| exercise `today_records.distance_km` | mock（无距离列）| 加列 `distance_km` |
| exercise `advice.*` | mock | LLM/agent |
| exercise `achievement.percentile` | mock | 跨用户人群聚合查询 |
| nutrition `meals[]`（分餐+单品 name/grams/calories）| mock（`nutrition_logs` 仅日级汇总+diet_narrative）| **核心**：新增 `meal_items` 表 或 nutrition_logs 分餐行 + 结构化 `recognized_foods`；与 `/chat` 多模态录入路径打通；食物名对齐图标集 |
| nutrition `exercise_advice`（训练方案 组次）| mock（agent 产出缺口）| 接 exercise_coach agent |

**配套：** 重启后端进程以反映 energy_gap 修复；goals 缺省常量(10000/60/2000/500) 与 seed 旧值(8000/30/1800/500) 第三层重刷对齐；"今日取最新行"会被"仅录睡眠"的行遮蔽运动总览，第三层重刷/调取数时处理。
