// 饮食管理页取数接口
import { getJson } from './http'
import type { NutritionResponse } from './types'

/** 饮食管理页数据聚合（纯 DB + mock）；date 缺省取今天 */
export function getNutrition(userId: number, date?: string): Promise<NutritionResponse> {
  const q = date ? `?date=${date}` : ''
  return getJson<NutritionResponse>(`/nutrition/${userId}${q}`)
}
