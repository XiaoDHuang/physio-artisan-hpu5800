// 报告 / 看板取数接口
import { getJson } from './http'
import type { DashboardResponse, ReportResult } from './types'

/** 看板数据聚合（纯 DB，毫秒级，不触发工作流） */
export function getDashboard(userId: number): Promise<DashboardResponse> {
  return getJson<DashboardResponse>(`/dashboard/${userId}`)
}

/** 最近一次已生成的报告（落库缓存）；无报告时后端返回 404 */
export function getLatestReport(userId: number): Promise<ReportResult> {
  return getJson<ReportResult>(`/report/latest/${userId}`)
}
