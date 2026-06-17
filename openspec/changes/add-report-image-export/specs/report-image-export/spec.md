## ADDED Requirements

### Requirement: 导出报告图片生成
系统 SHALL 在用户点击"导出报告"按钮时，收集当前报告页面的 KPI、身体指标、睡眠、饮食、运动、健康建议等数据，通过后端大模型多模态接口生成一张可视化的报告图片，并在前端展示和自动下载。

#### Scenario: 正常导出报告图片
- **WHEN** 用户点击 AppHeader 中的"导出报告"按钮
- **THEN** 前端从 Pinia useReportStore 收集所有报告数据，构造 JSON
- **AND** 前端 POST /api/report-image，body 为报告数据 JSON
- **AND** 按钮进入 loading 状态，显示"正在生成报告图片..."
- **AND** 后端收到数据后构造 prompt，调用大模型图片生成接口
- **AND** 后端返回 image/png 二进制数据
- **AND** 前端弹出预览弹窗展示生成的报告图片
- **AND** 浏览器自动触发图片下载（文件名为 report-<日期>.png）

#### Scenario: 后端不可用时显示错误
- **WHEN** 用户点击"导出报告"按钮且后端返回非 200 状态
- **THEN** 按钮退出 loading 状态
- **AND** 显示错误提示"报告图片生成失败，请稍后重试"

#### Scenario: 生成超时处理
- **WHEN** 图片生成请求超过 60 秒未响应
- **THEN** 前端中止请求
- **AND** 显示错误提示"生成超时，请稍后重试"

### Requirement: 大模型图片生成适配器
后端 SHALL 实现图片生成适配器，支持两种调用路径：优先使用 Chat Completions + modalities image，降级使用 /images/generations 标准端点。

#### Scenario: Chat Completions 图片生成成功
- **WHEN** 后端调用 `generate_report_image(data)` 且网关支持 `modalities: ["image"]`
- **THEN** 后端根据报告数据构造包含布局指令和设计风格的系统提示词
- **AND** 调用 Chat Completions API，modalities 设为 ["image"]
- **AND** 从响应中提取 image data（base64 → bytes）
- **AND** 返回完整 PNG 字节

#### Scenario: 降级到 /images/generations 端点
- **WHEN** Chat Completions 图片生成路径不可用或失败
- **THEN** 后端降级调用 `POST {base_url}/images/generations`
- **AND** 将报告数据转为简洁 prompt 文本
- **AND** 返回生成的图片字节

#### Scenario: 两种路径均失败
- **WHEN** Chat Completions 和 /images/generations 均不可用
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
- **AND** 文件名为 `健康报告-2026-06-01.png`（日期取自报告数据）

#### Scenario: 关闭预览
- **WHEN** 用户点击预览弹窗的"关闭"按钮或点击遮罩
- **THEN** 弹窗关闭，释放 ObjectURL
