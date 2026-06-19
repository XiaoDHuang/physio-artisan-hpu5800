/** 报告生成 Chat / 任务 — 用户向文案与工具函数 */

export type ReportTaskStatus = 'running' | 'completed' | 'failed' | 'timeout'

const REPORT_PATTERN = /报告|体检|健康分析|训练.*膳食|生成.*方案|身体分析/

export function looksLikeReportRequest(text: string): boolean {
  return REPORT_PATTERN.test(text.trim())
}

function todayLocal(): string {
  const d = new Date()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

/** ISO → 「今天」或「6月15日」 */
export function formatCnDate(iso: string): string {
  if (!iso) return ''
  if (iso === todayLocal()) return '今天'
  const [, mm, dd] = iso.split('-')
  return `${Number(mm)}月${Number(dd)}日`
}

export function mapStatusToProgress(status: string, progress: number): string {
  if (status === 'started') return '正在准备你的健康数据…'
  if (status === 'processing' && progress < 40) return '生理指标评估中…'
  if (status === 'processing' && progress < 70) return '运动与恢复方案生成中…'
  if (status === 'processing') return '膳食建议与报告汇总中…'
  return '正在生成报告…'
}

export function runningBannerLine(anchorDate: string, progressLine: string): string {
  return `🔄 ${formatCnDate(anchorDate)}报告生成中 · ${progressLine}`
}

export function successReply(anchorDate: string, userName?: string): string {
  const day = formatCnDate(anchorDate)
  if (userName) {
    return `✅ ${userName}，${day}的健康报告已生成！看板与健康建议已更新，向上滚动即可查看。`
  }
  return `✅ ${day}的健康报告已生成！看板与健康建议已更新，向上滚动即可查看。`
}

export function successToast(anchorDate: string, userName?: string): string {
  const day = formatCnDate(anchorDate)
  if (userName) return `${userName}，${day}的健康报告已生成`
  return `${day}的健康报告已生成`
}

export function failureReply(): string {
  return '❌ 报告暂时未能完成，请稍后重试。若多次失败，可切换日期或联系管理员。'
}

export function failureBanner(anchorDate: string): string {
  return `❌ ${formatCnDate(anchorDate)}报告生成未完成，请稍后重试`
}

export function timeoutReply(anchorDate: string): string {
  return `⏳ ${formatCnDate(anchorDate)}的报告仍在后台生成，你可以继续浏览；完成后切换日期或刷新页面即可看到最新建议。`
}

export function timeoutBanner(anchorDate: string): string {
  return `⏳ ${formatCnDate(anchorDate)}报告仍在后台生成中`
}

export function duplicateReportBlocked(anchorDate: string): string {
  return `${formatCnDate(anchorDate)}的报告正在生成中，请稍候再试。`
}

export function dateSwitchInfoToast(anchorDate: string): string {
  return `${formatCnDate(anchorDate)}的健康报告已生成，切换至该日期即可查看。`
}

export function completedBanner(anchorDate: string): string {
  return `✅ ${formatCnDate(anchorDate)}报告已生成`
}
