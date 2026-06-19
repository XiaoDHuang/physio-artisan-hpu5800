## Context

### 现状（as-is）

| 能力 | 是否支持当前切换日 |
|------|-------------------|
| 看板 KPI/睡眠/饮食/运动 | ✅ `store.load(date)` → `GET /dashboard?date=` |
| AI 健康建议展示 | ✅ `hasReport` + `anchor_date === date` 门控 |
| 导出按钮 | ❌ 始终可点（除 loading） |
| 导出 healthAdvice | ❌ 无报告时用三句硬编码占位 |
| 导出文件名 | ⚠️ 部分用 `new Date()` 而非看板日 |

```typescript
// useReportExport.ts — 问题片段
healthAdvice: {
  exercise: store.healthAdvice?.exercise || '每日30分钟有氧…',  // 占位
  ...
}
```

### 目标（to-be）

```
Header 日期 D + hasReport(D) === true  →  可导出，数据含 date=D + 真实 healthAdvice
Header 日期 D + hasReport(D) === false →  按钮 disabled，点击无请求
```

---

## Decisions

### D1：可导出判定

```typescript
canExportReport: (s) => s.hasReport && !s.loading && Boolean(s.date)
```

与 `HealthAdviceCard` 空态「该日暂无 AI 报告」口径一致：以 `/report/latest?date=` 是否 404 为准，**不看** dashboard 是否有 KPI。

### D2：前端门控，后端不加固

- 按钮 `disabled` + composable 内二次校验
- 无报告时若误触：`message.info('该日暂无 AI 报告，请先在下方对话中生成')`
- `/report-image` 请求体仍由前端组 JSON，不新增必填服务端校验（演示期）

### D3：导出 payload

在现有 JSON 顶层增加：

```json
{ "date": "2026-06-15", "kpi": {…}, "healthAdvice": { "exercise": "…", … } }
```

`healthAdvice` **必须**来自 `store.healthAdvice`（三字段均有值才导出）；不再使用 placeholder。

### D4：UX

| 状态 | 按钮 | 提示 |
|------|------|------|
| `loading` | disabled | — |
| `!hasReport` | disabled | `title="该日暂无 AI 报告，请先生成后再导出"` |
| `hasReport` | 可点 | 正常 loading 文案 |

下载文件名：`健康报告-${store.date}.png`

### D5：导出进行中切换日期（方案 B）

| 动作 | 行为 |
|------|------|
| 用户切日 | 关闭预览 + **abort** 进行中的 `/report-image`（静默，无错误 toast） |
| 请求完成且 `viewingDate === anchorDate` | 弹预览 + success toast |
| 请求完成但用户已切走（未 abort 的竞态） | 不弹预览，revoke ObjectURL + info toast |
| 下载文件名 | 使用 **导出锚点日** `previewAnchorDate`，非当前看板日 |

```typescript
cancelExportOnDateSwitch()  // watch(date) 调用
exportReportImage() → ExportOutcome: preview | dismissed | cancelled | failed
```

---
## Risks

| 风险 | 缓解 |
|------|------|
| 有 report 但 healthAdvice 字段空 | `canExportReport` 可收紧为 `hasReport && healthAdvice` |
| 用户切日后旧预览 modal 仍打开 | 已有 `watch(reloadVersion)`；补充 `watch(date)` 关闭 preview |

---

## Migration

1. store getter + composable 校验 + 去 placeholder
2. ReportView 按钮 disabled / title / watch date 关 preview
3. 文档 + 手动：有报告日导出 / 无报告日按钮灰
