// 底部聊天框状态（Pinia）— 单轮问答、覆盖式
//
// 需求（docs/frontend/design.md §6）：
// - 只显示当前一问一答；输入框下方只显示最新机器人回答，再次输入即覆盖。
// - 用临时 conversation_id（仅内存）：首次为空 → 后端创建并回传；丢失则重建。
// - 报告长任务与单轮 Chat 解耦（improve-report-chat-replies D9–D11）

import { defineStore } from 'pinia'
import { message } from 'ant-design-vue'
import { postChat } from '@/api/chat'
import { getTaskStatus } from '@/api/plan'
import type { ChatIntent } from '@/api/types'
import { useReportStore } from '@/stores/report'
import {
  looksLikeReportRequest,
  mapStatusToProgress,
  successReply,
  successToast,
  failureReply,
  failureBanner,
  timeoutReply,
  timeoutBanner,
  duplicateReportBlocked,
  dateSwitchInfoToast,
  completedBanner,
  type ReportTaskStatus,
} from '@/copy/reportChat'

export interface ChatSendContext {
  userId?: number
  date?: string
  userName?: string
  onReportComplete?: () => void | Promise<void>
}

export interface ActiveReportTask {
  taskId: string
  userId: number
  anchorDate: string
  progressLine: string
  status: ReportTaskStatus
  bannerLine: string
  userName?: string
}

const BANNER_DISMISS_MS = 3000
const POLL_INTERVAL_MS = 2000
const POLL_MAX = 90

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms))
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    conversationId: null as string | null,
    sending: false,
    lastQuestion: '' as string,
    lastReply: '' as string,
    lastIntent: '' as ChatIntent | '',
    activeReportTask: null as ActiveReportTask | null,
    /** 递增加以忽略 reset / 新任务 后的过期轮询 */
    pollGeneration: 0,
    _bannerDismissTimer: null as ReturnType<typeof setTimeout> | null,
  }),

  getters: {
    isReportRunning: (s) => s.activeReportTask?.status === 'running',
  },

  actions: {
    clearConversationUi() {
      this.lastQuestion = ''
      this.lastReply = ''
      this.lastIntent = ''
    },

    _clearBannerDismissTimer() {
      if (this._bannerDismissTimer) {
        clearTimeout(this._bannerDismissTimer)
        this._bannerDismissTimer = null
      }
    },

    _scheduleBannerDismiss() {
      this._clearBannerDismissTimer()
      this._bannerDismissTimer = setTimeout(() => {
        if (this.activeReportTask?.status !== 'running') {
          this.activeReportTask = null
        }
        this._bannerDismissTimer = null
      }, BANNER_DISMISS_MS)
    },

    _setTerminalTask(
      status: Exclude<ReportTaskStatus, 'running'>,
      bannerLine: string,
      updateReply?: string,
    ) {
      if (!this.activeReportTask) return
      this.activeReportTask = {
        ...this.activeReportTask,
        status,
        bannerLine,
        progressLine: '',
      }
      if (updateReply !== undefined && this.lastIntent === 'report') {
        this.lastReply = updateReply
      }
      this._scheduleBannerDismiss()
    },

    async onReportTaskSettled(
      task: ActiveReportTask,
      outcome: 'completed' | 'failed' | 'timeout',
      ctx?: ChatSendContext,
    ) {
      const reportStore = useReportStore()
      const viewingDate = reportStore.date

      if (outcome === 'completed') {
        if (viewingDate === task.anchorDate) {
          await reportStore.load(task.anchorDate, task.userId)
          message.success(successToast(task.anchorDate, task.userName))
          this._setTerminalTask(
            'completed',
            completedBanner(task.anchorDate),
            successReply(task.anchorDate, task.userName),
          )
        } else {
          message.info(dateSwitchInfoToast(task.anchorDate))
          this._setTerminalTask('completed', completedBanner(task.anchorDate))
        }
        await ctx?.onReportComplete?.()
      } else if (outcome === 'failed') {
        message.error('报告生成未完成，请稍后重试')
        this._setTerminalTask(
          'failed',
          failureBanner(task.anchorDate),
          this.lastIntent === 'report' ? failureReply() : undefined,
        )
      } else {
        message.warning('报告仍在后台生成，请稍后刷新或切换日期查看')
        this._setTerminalTask(
          'timeout',
          timeoutBanner(task.anchorDate),
          this.lastIntent === 'report' ? timeoutReply(task.anchorDate) : undefined,
        )
      }
    },

    startReportPoll(taskId: string, ctx?: ChatSendContext) {
      const userId = ctx?.userId ?? 1
      const anchorDate = ctx?.date ?? ''
      this._clearBannerDismissTimer()
      this.pollGeneration += 1
      const gen = this.pollGeneration

      this.activeReportTask = {
        taskId,
        userId,
        anchorDate,
        progressLine: '正在准备你的健康数据…',
        status: 'running',
        bannerLine: '',
        userName: ctx?.userName,
      }

      void this.runReportPoll(taskId, gen, ctx)
    },

    async runReportPoll(taskId: string, gen: number, ctx?: ChatSendContext) {
      for (let i = 0; i < POLL_MAX; i++) {
        await sleep(POLL_INTERVAL_MS)
        if (gen !== this.pollGeneration) return
        if (this.activeReportTask?.taskId !== taskId) return

        try {
          const st = await getTaskStatus(taskId)
          if (gen !== this.pollGeneration) return

          const progressLine = mapStatusToProgress(st.status, st.progress)
          if (this.activeReportTask?.status === 'running') {
            this.activeReportTask = {
              ...this.activeReportTask,
              progressLine,
            }
          }

          if (st.status === 'completed') {
            const task = this.activeReportTask!
            await this.onReportTaskSettled(task, 'completed', ctx)
            return
          }
          if (st.status === 'failed') {
            const task = this.activeReportTask!
            await this.onReportTaskSettled(task, 'failed', ctx)
            return
          }
        } catch {
          // 轮询偶发失败时继续重试
        }
      }

      if (gen !== this.pollGeneration) return
      if (this.activeReportTask?.taskId !== taskId) return
      const task = this.activeReportTask!
      await this.onReportTaskSettled(task, 'timeout', ctx)
    },

    async send(text: string, ctx?: ChatSendContext) {
      const msg = text.trim()
      if (!msg || this.sending) return

      // 场景 2：进行中的报告 — 前端拦截重复 report 请求
      if (this.isReportRunning && looksLikeReportRequest(msg)) {
        this.lastQuestion = msg
        this.lastReply = duplicateReportBlocked(this.activeReportTask!.anchorDate)
        return
      }

      this.sending = true
      this.lastQuestion = msg
      this.lastReply = ''
      try {
        const resp = await postChat({
          message: msg,
          conversation_id: this.conversationId,
          user_id: ctx?.userId,
          date: ctx?.date,
        })
        this.conversationId = resp.conversation_id
        this.lastReply = resp.reply
        this.lastIntent = resp.intent

        if (resp.intent === 'report' && resp.task_id) {
          this.startReportPoll(resp.task_id, {
            ...ctx,
            date: resp.anchor_date || ctx?.date,
          })
        }
      } catch (e) {
        this.lastReply = `出错了：${e instanceof Error ? e.message : '请求失败'}`
        this.lastIntent = ''
      } finally {
        this.sending = false
      }
    },

    reset() {
      this.pollGeneration += 1
      this._clearBannerDismissTimer()
      this.conversationId = null
      this.lastQuestion = ''
      this.lastReply = ''
      this.lastIntent = ''
      this.activeReportTask = null
    },
  },
})
