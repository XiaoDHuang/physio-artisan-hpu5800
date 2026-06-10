# 前端设计方案 · 健康报告会话页

> 目标：按 `健康报告会话页.jpg` 实现左右布局——左侧导航菜单 + 右侧"健康报告"页（KPI/身体指标/卡片壳/底部聊天框）。
> 本文档为**实现前的设计稿**，确认后进入编码。

参考：[接口契约](../接口契约.md) · 后端 `backend/api_server.py`

---

## 0. 现状与关键决策

| 现状 | 处理 |
|---|---|
| 已有 `ChatSidebar/ChatPanel/MessageList` + `stores/chat.ts`（多会话历史列表 UI）| **不复用**该交互；左侧改为导航菜单，聊天改为底部单轮问答 |
| 现有 `api/chat.ts` 按 **SSE 流式**解析 `/chat` | ⚠️ 后端 `/chat` 已改为**一次性 JSON**(`ChatResponse`)，**重写** `api/chat.ts` |
| `package.json` 无 `vue-router` | **新增依赖** `vue-router@4`（路由级跳转）|
| `App.vue` 为扁平 `Sidebar+Panel` | 重构为 `AppLayout`（左导航 + `<RouterView/>`）|
| `vite.config.ts` 代理 `target: http://backend:8000` | docker 用；**本地 dev 需改 `localhost:8000`**（或用 env），实现阶段确认 |

**资产已就位**（`src/assets/`）：`logo/logo.png`、`nav-bar/健康报告.png`、`top-4-kpi-icon/*`、`physical-indicators-overview/*`。

---

## 1. 技术栈

- Vue 3 + TypeScript + Vite（现有）
- 状态：Pinia（现有）
- UI：ant-design-vue（现有；本页主要用原生 + 少量 antd 组件）
- 路由：**vue-router@4**（新增）
- 数据请求：原生 `fetch` 封装（轻量，无需 axios）

---

## 2. 目录规划

```
src/
├── main.ts                      # 注册 pinia / router / antd
├── App.vue                      # 仅 <ConfigProvider> + <RouterView/>
├── router/
│   └── index.ts                 # 路由表（健康报告 + 3 个占位）
├── layouts/
│   └── AppLayout.vue            # 左侧 SideNav + 右侧 <RouterView/> 主体
├── views/
│   ├── ReportView.vue           # 健康报告页（本期实现）
│   ├── ExerciseView.vue         # 运动分析（占位空白）
│   ├── SleepView.vue            # 睡眠监测（占位空白）
│   └── NutritionView.vue        # 饮食管理（占位空白）
├── components/
│   ├── nav/
│   │   └── SideNav.vue          # logo + 菜单项（路由跳转，高亮当前）
│   └── report/
│       ├── ReportHeader.vue     # 标题头 + 中间占位按钮（不交互）
│       ├── KpiCards.vue         # 顶部 4 个 KPI 卡（带图标）
│       ├── BodyOverview.vue     # 身体指标概览（人体 bg + 6 指标图标）
│       ├── SectionCard.vue      # 通用卡片壳（阴影/圆角/标题）——睡眠/饮食等占位用
│       └── ChatDock.vue         # 底部聊天框（单轮问答）
├── api/
│   ├── http.ts                  # fetch 封装（BASE=/api、错误处理）
│   ├── report.ts                # getLatestReport(uid) / getDashboard(uid)
│   ├── chat.ts                  # 重写：postChat() 返回 JSON ChatResponse
│   └── types.ts                 # ChatResponse / ReportResult / Dashboard 等类型
├── stores/
│   ├── report.ts                # 报告/看板数据 + 取数（latest→dashboard 回退）
│   └── chat.ts                  # 重写：单轮问答（临时会话ID、覆盖式）
└── assets/ …                    # 已有图标资源
```

> 旧文件 `components/ChatSidebar.vue`、`ChatPanel.vue`、`MessageList.vue` 及旧 `stores/chat.ts` 在本期不再挂载；
> 可保留代码备查，或实现阶段删除（倾向删除，避免误用 SSE 版）。

---

## 3. 路由设计（route-level 跳转）

`router/index.ts`，全部挂在 `AppLayout` 下，右侧 `<RouterView/>` 切换：

| path | name | 菜单名 | 组件 | 状态 |
|---|---|---|---|---|
| `/` | — | — | 重定向到 `/report` | — |
| `/report` | report | 健康报告 | `ReportView` | ✅ 本期实现 |
| `/exercise` | exercise | 运动分析 | `ExerciseView` | 占位（右侧空白）|
| `/sleep` | sleep | 睡眠监测 | `SleepView` | 占位（右侧空白）|
| `/nutrition` | nutrition | 饮食管理 | `NutritionView` | 占位（右侧空白）|

- 菜单点击 = `router.push`，`SideNav` 用 `useRoute()` 高亮当前项。
- 占位 View = 一个居中"功能建设中"空状态，便于演示跳转。

---

## 4. 布局与组件拆分

### 4.1 AppLayout（左右两栏）
```
┌──────────┬─────────────────────────────────────────┐
│ SideNav  │  ReportHeader（标题 + 占位按钮）          │
│  logo    │  ┌─────────────────────────────────────┐ │
│  ───     │  │ KpiCards（4 卡）                     │ │
│ 健康报告 │  ├──────────────────┬──────────────────┤ │
│ 运动分析 │  │ BodyOverview     │ SectionCard壳×N   │ │
│ 睡眠监测 │  │ (身体指标概览)    │ (睡眠/饮食/运动…) │ │
│ 饮食管理 │  └──────────────────┴──────────────────┘ │
│          │  ChatDock（底部聊天框，固定在内容区底部） │
└──────────┴─────────────────────────────────────────┘
```
- 左栏固定宽（约 200–220px），右栏 `flex:1` 可滚动；ChatDock 吸底。

### 4.2 SideNav
- 顶部：`logo/logo.png` + 文案"数建云"。
- 菜单项：健康报告（用 `nav-bar/健康报告.png` 图标）/ 运动分析 / 睡眠监测 / 饮食管理。
- 其余三项暂无专属图标 → 用 antd 图标或同色占位；高亮当前路由。

### 4.3 ReportHeader
- 左：页面标题"健康报告" + 副标题。
- 中：几个按钮**纯占位**（如"一键生成/导出/分享"），`disabled` 或无 `@click`，不做交互。

### 4.4 KpiCards（4 卡，带图标）— ✅ 绑数据
| 卡片 | 左上图标 | 右下装饰 | 数据字段（dashboard.kpi）|
|---|---|---|---|
| 综合健康评分 | `top-4-kpi-icon/综合健康评分.png` | — | `health_score` /100，副文 `score_delta_vs_last_week`（较上周↑N）|
| 身体状态 | `身体状态.png` | `身体状态-righ-bottom.png` | `status`（活力充沛…）|
| 运动达标率 | `运动达标率.png` | — | `exercise_rate`%，副文 `exercise_rate_delta` |
| 健康风险 | `健康风险.png` | `健康风险-right-bottom.png` | `risk`（低风险…），副文"一切指标正常"|

### 4.5 BodyOverview（身体指标概览）— ✅ 绑数据
- 背景：`physical-indicators-overview/physical-indicators-overview-bg.png`（人体剪影）。
- 6 个指标环绕，图标 + 数值（数据 `dashboard.body_overview`）：

| 指标 | 图标 | 字段 |
|---|---|---|
| 心率 | `心率.png` | `heart_rate` 次/分 |
| 体重 | `体重.png` | `weight_kg` kg |
| BMI | `BMI.png` | `bmi` |
| 基础代谢 | `基础代谢.png` | `bmr` 千卡 |
| 体脂率 | `体脂率.png` | `body_fat_pct` % |
| 肌肉量 | `肌肉量.png` | `muscle_mass_kg` kg |

- 底部一行"数据来源 / 更新时间"：`update_date`（设备名暂留静态文案）。

### 4.6 SectionCard（睡眠监测等其余卡）— 仅壳，不填充
- 通用卡片组件：白底、圆角、阴影、可选标题（如"睡眠监测""饮食监测""运动监测""健康建议""明日饮食建议""运动建议"）。
- 本期 `body` 留空（或骨架占位），**不绑数据**。后续报告生成后再填充 LLM 内容。

### 4.7 ChatDock（底部聊天框，单轮问答）
见第 6 节交互逻辑。

---

## 5. 数据流（取数与回退）

`stores/report.ts` 暴露 `dashboard`（KPI/身体面板归一化后的对象）、`hasReport`、`loading`。

```
ReportView onMounted → reportStore.load(USER_ID=1)
  1) GET /api/report/latest/1
       200 → hasReport=true；result.final_report.chart_data.dashboard → dashboard
              （同时缓存 result，供后续 LLM 卡片填充用）
       404 → 进入 2)
  2) GET /api/dashboard/1
       200 → hasReport=false；resp.dashboard → dashboard
```

- **本期只绑两块**：`KpiCards ← dashboard.kpi`、`BodyOverview ← dashboard.body_overview`。
- 其余 SectionCard 壳不绑数据。
- **LLM 报告部分**（rs_gauge / trend_dual / radar_compare / cards 训练·三餐·睡眠建议 / vocal_narrative）：
  本期不渲染；待 `/report/latest` 有数据后，下一阶段再把这些填进对应卡片。
- 固定 `USER_ID = 1`（常量，后续接用户态再改）。

字段缺失（如某些值为 null）→ 显示"—"占位，不报错。

---

## 6. 底部聊天框交互逻辑（ChatDock + stores/chat 重写）

需求：只显示**当前一问一答**，输入框底部只显示**最新机器人回答**，再次输入即覆盖。

`stores/chat.ts`（精简重写）：
```ts
state: { conversationId: string | null, sending: boolean, lastReply: string }
```
- `conversationId` 初始 `null`（临时会话，仅内存保存；刷新/丢失则重建，符合"会话ID丢了就重新创建"）。
- `send(text)`：
  1. `sending=true`，清空 `lastReply`（或显示"思考中…"）。
  2. `POST /api/chat { message: text, conversation_id: conversationId }`。
  3. 拿到 `ChatResponse`：`conversationId = resp.conversation_id`（首次创建即回填）；`lastReply = resp.reply`（**覆盖**上一次）。
  4. `sending=false`。
- UI：输入框 + 其下方一行展示 `lastReply`（单条，覆盖式）。无历史气泡列表。

> `/chat` 现为 JSON（非 SSE），`api/chat.ts` 重写为：
> ```ts
> export async function postChat(req: {message:string; conversation_id?:string|null})
>   : Promise<ChatResponse>   // 直接 await resp.json()
> ```
> intent 处理本期最简：直接显示 `resp.reply`。
> （后续增强：当 `resp.intent==='report'` 且有 `task_id` → 轮询 `/status` 完成后刷新报告页；本期不做。）

---

## 7. 类型定义（api/types.ts，节选）

```ts
export interface ChatResponse {
  conversation_id: string
  intent: 'report' | 'data_entry' | 'other' | 'blocked'
  data_type: string | null
  reply: string
  extracted: Record<string, any>
  missing: string[]
  can_proceed: boolean
  saved: boolean
  task_id: string | null
}

export interface DashboardKpi {
  health_score: number; score_delta_vs_last_week: number | null
  status: string; exercise_rate: number; exercise_rate_delta: number | null; risk: string
}
export interface BodyOverview {
  heart_rate: number|null; weight_kg: number|null; bmi: number|null
  bmr: number|null; body_fat_pct: number|null; muscle_mass_kg: number|null; update_date: string|null
}
export interface Dashboard {
  kpi: DashboardKpi; body_overview: BodyOverview
  sleep: any; nutrition: any; exercise_today: any; week_summary: any; goals: any
}
// /report/latest 返回的 result（结构见接口契约 §4），本期只取 final_report.chart_data.dashboard
```

---

## 8. 实现分期（确认后执行）

1. **脚手架**：装 `vue-router`；改 `main.ts`/`App.vue`；建 `router/`、`AppLayout`、4 个 view（占位）、`SideNav`。验证路由跳转。
2. **取数层**：`api/http.ts` + `api/report.ts` + `stores/report.ts`（latest→dashboard 回退）。
3. **报告页静态结构**：`ReportHeader` + `KpiCards` + `BodyOverview` + N 个 `SectionCard` 壳（阴影/背景/标题）。
4. **绑数据**：KPI 卡 + 身体指标概览接 `dashboard`。
5. **聊天框**：重写 `api/chat.ts`（JSON）+ `stores/chat.ts`（单轮覆盖）+ `ChatDock`。
6. 自测：`/report`正常渲染 KPI/身体；切换 4 个菜单路由生效；底部问答可用、覆盖式。

---

## 9. 本期边界（明确不做）

- 其余卡片（睡眠/饮食/运动监测、健康建议、明日饮食、运动建议）**只做壳**，不填内容。
- LLM 报告可视化（仪表盘/趋势/雷达/三餐/训练方案/语音播报）**不渲染**。
- 运动分析/睡眠监测/饮食管理三个菜单**右侧空白**占位。
- 标题头中部按钮**不交互**。
- 无用户登录态，`user_id` 固定 1。
- 多模态图片上传暂不做（聊天仅文本）。
