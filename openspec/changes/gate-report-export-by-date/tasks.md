## 1. 状态与 composable

- [x] 1.1 `stores/report.ts` 增加 `canExportReport` getter
- [x] 1.2 `useReportExport`：导出前校验；payload 含 `date`；移除 healthAdvice 占位 fallback

## 2. UI

- [x] 2.1 `ReportView`：导出按钮绑定 `canExportReport`；无报告时 title 提示
- [x] 2.2 下载文件名使用 `store.date`；切日时关闭预览弹窗

## 3. 文档

- [x] 3.1 `docs/接口契约.md` 补充 report-image 导出前置条件与 `date` 字段

## 4. 验证

- [x] 4.1 有报告日可导出；无报告日按钮禁用（需本地手动点测）
- [x] 4.2 导出中切日 abort；完成时按锚点日门控预览（方案 B）
