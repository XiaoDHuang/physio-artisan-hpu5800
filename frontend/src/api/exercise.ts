// 运动分析页取数接口
import { getJson } from './http'
import type { ExerciseResponse } from './types'

/** 运动分析页数据聚合（纯 DB + mock，毫秒级，不触发工作流） */
export function getExercise(userId: number): Promise<ExerciseResponse> {
  return getJson<ExerciseResponse>(`/exercise/${userId}`)
}
