// 报告 / 看板取数接口
import { getJson } from './http'
import type { DashboardResponse, ReportResult } from './types'

/** 看板数据聚合（纯 DB，毫秒级，不触发工作流）；date 缺省取今天 */
export function getDashboard(userId: number, date?: string): Promise<DashboardResponse> {
  const q = date ? `?date=${date}` : ''
  return getJson<DashboardResponse>(`/dashboard/${userId}${q}`)
}

/** 已生成报告（落库缓存）；date 可选，按锚点日筛选 */
export function getLatestReport(userId: number, date?: string): Promise<ReportResult> {
  const q = date ? `?date=${date}` : ''
  return getJson<ReportResult>(`/report/latest/${userId}${q}`)
}
