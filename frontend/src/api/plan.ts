// 任务状态轮询（报告生成）
import { getJson } from './http'
import type { ReportResult } from './types'

export interface TaskStatusResponse {
  task_id: string
  status: string
  progress: number
  message: string
  result: ReportResult | null
}

export function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  return getJson<TaskStatusResponse>(`/status/${taskId}`)
}
