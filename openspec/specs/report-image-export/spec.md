# report-image-export Specification

## Purpose

健康报告页按锚点日导出 LLM 生成的报告图片，经 `POST /api/report-image` 调用大模型图片生成。

## Requirements

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

### Requirement: 导出报告图片生成

系统 SHALL 在用户点击"导出报告"按钮时，收集**当前看板锚点日**的报告页面数据（含该日 AI 健康建议），通过后端大模型图片生成接口生成一张可视化的报告图片，并在前端展示和下载。

仅当当前选中日期存在已生成的 AI 报告（`hasReport`）时才允许导出；**不得**使用占位默认健康建议文案填充导出数据。

#### Scenario: 正常导出报告图片

- **WHEN** 用户在有 AI 报告的日期 D 点击 AppHeader 中的"导出报告"按钮
- **THEN** 前端从 Pinia useReportStore 收集日期 D 的看板数据与真实 healthAdvice，构造 JSON（含 `date: D`）
- **AND** 前端 POST /api/report-image
- **AND** 按钮进入 loading 状态，显示"正在生成报告图片..."
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

#### Scenario: 后端不可用时显示错误

- **WHEN** 用户点击"导出报告"按钮且后端返回非 200 状态
- **THEN** 按钮退出 loading 状态
- **AND** 显示错误提示"报告图片生成失败，请稍后重试"

#### Scenario: 生成超时处理

- **WHEN** 图片生成请求超过配置超时未响应
- **THEN** 前端中止请求
- **AND** 显示错误提示"生成超时，请稍后重试"

### Requirement: 大模型图片生成适配器

后端 SHALL 实现图片生成适配器，调用 `POST {base_url}/images/generations`（或网关支持的等价端点），根据报告数据构造 prompt，返回 PNG 字节。

#### Scenario: 图片生成成功

- **WHEN** 后端调用 `generate_report_image(data)` 且上游可用
- **THEN** 返回完整 PNG 字节

#### Scenario: 上游失败

- **WHEN** 图片生成不可用
- **THEN** 后端抛出 ImageGenError 异常
- **AND** API 路由返回 502 错误给前端

### Requirement: 报告图片预览与下载

系统 SHALL 在图片生成成功后弹出预览窗口，并提供下载按钮。下载触发应为自动的，预览窗口提供二次手动下载的能力。

#### Scenario: 图片生成后弹出预览

- **WHEN** 后端成功返回报告图片
- **THEN** 前端弹出居中预览弹窗
- **AND** 弹窗包含：生成的报告图片（最大 90vw/90vh）+ [下载] [关闭] 按钮

#### Scenario: 浏览器自动下载

- **WHEN** 预览弹窗展示
- **THEN** 浏览器自动触发一次下载（使用隐藏 `<a>` + `download` 属性）
- **AND** 文件名为 `健康报告-{date}.png`（日期取自报告数据）

#### Scenario: 关闭预览

- **WHEN** 用户点击预览弹窗的"关闭"按钮或点击遮罩
- **THEN** 弹窗关闭，释放 ObjectURL
