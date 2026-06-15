// 睡眠监测页取数 / 录入接口
import { getJson, postJson } from './http'
import type { SleepResponse, SleepEntryPayload, SleepEntryResult } from './types'

export type SleepRangeOpt = '7d' | '14d'

/** 睡眠监测页数据聚合（纯 DB + mock） */
export function getSleep(userId: number, range: SleepRangeOpt = '7d'): Promise<SleepResponse> {
  return getJson<SleepResponse>(`/sleep/${userId}?range=${range}`)
}

/** 手动录入睡眠记录（写 watch_data.sleep_data JSONB） */
export function postSleepEntry(payload: SleepEntryPayload): Promise<SleepEntryResult> {
  return postJson<SleepEntryResult>('/sleep/entry', payload)
}
