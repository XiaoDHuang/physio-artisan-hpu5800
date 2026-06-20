## ADDED Requirements

### Requirement: Report image export SHALL require AI report for current dashboard date

The client SHALL enable the "导出报告" action only when the report page is viewing date D and `GET /report/latest?date=D` has succeeded (`hasReport === true`).

When no AI report exists for the selected date, the export button SHALL be disabled and the client SHALL NOT call `POST /report-image`.

#### Scenario: User selects date with cached AI report

- **WHEN** the dashboard date is D and `hasReport` is true for D
- **THEN** the export button is enabled
- **AND** export payload includes `date: D` and real `healthAdvice` from the cached report

#### Scenario: User selects date without AI report

- **WHEN** the dashboard date is D and `hasReport` is false
- **THEN** the export button is disabled
- **AND** no `/report-image` request is sent

---

## MODIFIED Requirements

### Requirement: 导出报告图片生成

系统 SHALL 在用户点击"导出报告"按钮时，收集**当前看板锚点日**的报告页面数据（含该日 AI 健康建议），通过后端大模型多模态接口生成一张可视化的报告图片，并在前端展示和下载。

仅当当前选中日期存在已生成的 AI 报告（`hasReport`）时才允许导出；**不得**使用占位默认健康建议文案填充导出数据。

#### Scenario: 正常导出报告图片

- **WHEN** 用户在有 AI 报告的日期 D 点击 AppHeader 中的"导出报告"按钮
- **THEN** 前端从 Pinia useReportStore 收集日期 D 的看板数据与真实 healthAdvice，构造 JSON（含 `date: D`）
- **AND** 前端 POST /api/report-image
- **AND** 下载文件名为 `健康报告-D.png`

#### Scenario: 无 AI 报告时不可导出

- **WHEN** 当前看板日期无 `/report/latest?date=` 缓存
- **THEN** 导出按钮为 disabled 状态
- **AND** 不发起图片生成请求

#### Scenario: 导出进行中用户切换看板日期

- **WHEN** 用户在有 AI 报告的日期 D1 点击导出且请求尚未完成
- **AND** 用户将看板切换到日期 D2
- **THEN** 客户端 abort 进行中的 `/report-image` 请求且不展示错误 toast
- **AND** 关闭已打开的预览弹窗
- **WHEN** 请求在 abort 前完成且看板仍为 D1
- **THEN** 展示预览弹窗且下载文件名为 `健康报告-D1.png`
- **WHEN** 请求在 abort 前完成但看板已切到 D2
- **THEN** 不展示预览弹窗
- **AND** 显示 informational toast 提示切换至 D1 后可再次导出查看
