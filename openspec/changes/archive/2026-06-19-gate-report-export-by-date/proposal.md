## Why

`add-report-dashboard-by-date` 与 `add-chat-report-by-date` 已支持报告页按锚点日查看看板与 AI 健康建议，但 **「导出报告」未与当前日是否有 AI 报告对齐**：

- 导出按钮仅受 `isLoading` 控制，**无报告日仍可点击**
- `useReportExport.buildReportData()` 在 `healthAdvice` 缺失时使用**硬编码占位文案**，导出的图片并非真实 AI 报告内容
- 下载文件名未稳定使用当前看板 `date`（仍部分取 `new Date()`）
- **导出进行中切日** 可能弹出错误日期的预览图，或文件名与图片内容不一致

用户期望：**仅当当前选中日期已有 AI 报告（`GET /report/latest?date=` 命中）时才允许导出**；导出数据对应当前 Header 日期；切日时不误展示其他日的导出结果。

## What Changes

- **新增** `reportStore.canExportReport`：`hasReport === true` 且非 loading
- **改造** `ReportView`：无报告时禁用「导出报告」按钮，并给出 title/提示
- **改造** `useReportExport`：导出前校验 `canExportReport`；`healthAdvice` 仅用 store 真实数据（去掉占位 fallback）；payload 增加 `date` 字段
- **改造** 下载文件名：`健康报告-{anchorDate}.png`（导出锚点日，预览下载与图片内容一致）
- **方案 B（导出中切日）**：切日 → 关闭预览 + **abort** 进行中 `/report-image`（静默）；完成时仅当看板日 = 导出锚点日才弹预览，否则 info toast
- **同步** `docs/接口契约.md`（report-image 前置条件、`date` 字段、切日约定）

## 与相关变更的关系

| 变更 | 职责 |
|------|------|
| `add-report-image-export` | 底座：`POST /report-image`、图片生成适配器、基础导出 UI |
| `add-report-dashboard-by-date` | 看板锚点日 `reportStore.date` |
| `add-chat-report-by-date` | 按日生成 AI 报告 → `hasReport` |
| **本变更** | 导出与锚点日 / `hasReport` 对齐 + 切日 abort 与预览门控 |

归档时：先 `add-report-image-export`（ADDED），再本变更（MODIFIED `report-image-export`）。

## Capabilities

### New Capabilities

- `report-export-by-date`：导出报告图片与当前看板锚点日及 AI 报告缓存绑定，无报告不可导出

### Modified Capabilities

- `report-image-export`：导出前置条件、payload 含 `date`、禁止占位健康建议、**切日方案 B**（abort + 预览门控）

## Impact

| 层级 | 文件 |
|------|------|
| 前端 store | `stores/report.ts` — `canExportReport` |
| 前端 composable | `composables/useReportExport.ts` |
| 前端页面 | `views/ReportView.vue` |
| 文档 | `docs/接口契约.md` |

## Out of Scope

- 后端 `/report-image` 强制校验 `date`（本期前端门控即可）
- 无报告日仍允许导出「纯看板截图」（用户明确要求不支持）
- 切回锚点日自动复用未展示的 ObjectURL（演示期不缓存，需再次点击导出）
