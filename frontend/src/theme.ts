// 主题色板 —— 取自参考图的绿色健康风
// 主色为清新薄荷绿，背景为极浅灰绿，卡片为白。

export const theme = {
  // 主色（按钮、强调、用户气泡）
  primary: '#3fbf8f',
  primaryHover: '#34a87c',
  primaryActive: '#2c9069',
  // 浅主色（hover 背景、选中态）
  primarySoft: '#e8f7f1',
  primarySoftHover: '#d8f0e6',
  // 背景层
  appBg: '#f3f8f6', // 整体页面底色（浅灰绿）
  sidebarBg: '#ffffff', // 左侧历史栏
  panelBg: '#f7faf9', // 右侧聊天区底
  cardBg: '#ffffff',
  // 文本
  text: '#1f2d28',
  textSecondary: '#6b7d76',
  textTertiary: '#9aa8a2',
  // 边框/分隔线
  border: '#e6efea',
  // 圆角
  radius: 12,
} as const

// 注入到 ant-design-vue ConfigProvider 的 token
export const antdThemeToken = {
  colorPrimary: theme.primary,
  colorInfo: theme.primary,
  borderRadius: theme.radius,
  colorBgLayout: theme.appBg,
  fontSize: 14,
}
