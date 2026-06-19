// 语音输入 composable —— 真录音(getUserMedia/MediaRecorder) + 实时波形 + 计时 + 转写
//
// 两层设计（详见 openspec/changes/add-voice-input-mock）：
//   transcribe(blob) 是唯一替换点。
//   - Layer 1（本期）：VOICE_USE_MOCK = true → setTimeout 返回示例文本。
//   - Layer 2（后端就绪后）：把 VOICE_USE_MOCK 置 false → 走 POST /api/asr。
// 返回结构两层一致：{ text }，故 dock 处理逻辑不变。

import { ref, onUnmounted } from 'vue'

export type VoiceState = 'idle' | 'requesting' | 'recording' | 'transcribing' | 'error'

// Layer 1 开关：true=本地模拟；后端(/api/asr)接好后置 false 即切真实。
// 置 false 需后端运行，纯前端演示可切回 true。
const VOICE_USE_MOCK = false

// 无麦克风/无权限时的演示回退（仅 VOICE_USE_MOCK=true 时生效）。
// 真实 ASR 模式下应置 false，否则会静默走 mock 转写、看不到 /api/asr 请求。
const VOICE_DEMO_FALLBACK = false

const BARS = 18 // 波形条数

export interface VoiceOptions {
  mockSamples?: string[]
  maxSeconds?: number
}

function pickMime(): string {
  const cands = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg']
  if (typeof MediaRecorder !== 'undefined') {
    for (const c of cands) if (MediaRecorder.isTypeSupported(c)) return c
  }
  return ''
}

/** 启动录音前检查；返回可读错误文案，通过则返回 null */
function getRecordingSupportError(): string | null {
  if (typeof window === 'undefined') return '当前环境不支持录音'
  // getUserMedia / MediaRecorder 仅在「安全上下文」可用（https 或 localhost/127.0.0.1）
  if (!window.isSecureContext) {
    const url = `${window.location.protocol}//${window.location.host}`
    return `语音需要安全连接。当前 ${url} 不可用，请改用 http://localhost:8080 或 https 访问（勿用局域网 IP）`
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    return '当前浏览器未开放麦克风 API，请用 Chrome / Edge 打开，并避免 IDE 内置预览窗'
  }
  if (typeof MediaRecorder === 'undefined') {
    return '当前浏览器不支持录音编码（MediaRecorder），请升级 Chrome / Edge'
  }
  return null
}

let _mockIdx = 0

/**
 * 浏览器 MediaRecorder 产出的 webm/opus / ogg 容器 → qwen3-omni-flash
 * 的 input_audio 不可靠；用 Web Audio API 解码 + 降采样 16kHz mono + 封 WAV。
 *
 * 16kHz 对语音 ASR 足够，且把文件从 48k→16k 缩小 3×，避免 base64 过大
 * 导致 apiyi 网关 Read timed out。
 */
async function blobToWavBlob(blob: Blob): Promise<Blob> {
  const AC: typeof AudioContext =
    window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
  const ctx = new AC()
  try {
    const buf = await ctx.decodeAudioData(await blob.arrayBuffer())
    // 单声道混音
    const srcSr = buf.sampleRate
    const srcLen = buf.length
    const ch = buf.numberOfChannels
    const mono = new Float32Array(srcLen)
    for (let i = 0; i < srcLen; i++) {
      let sum = 0
      for (let c = 0; c < ch; c++) sum += buf.getChannelData(c)[i]
      mono[i] = sum / ch
    }
    // 降采样到 8kHz（语音 ASR 够用，且最小化 base64 体积避免网关超时）
    const targetSr = 8000
    const ratio = targetSr / srcSr
    const dstLen = Math.floor(srcLen * ratio)
    const pcm = new Int16Array(dstLen)
    for (let i = 0; i < dstLen; i++) {
      const pos = i / ratio
      const i0 = Math.floor(pos)
      const i1 = Math.min(i0 + 1, srcLen - 1)
      const frac = pos - i0
      const v = mono[i0] + (mono[i1] - mono[i0]) * frac
      const s = Math.max(-1, Math.min(1, v))
      pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff
    }
    // 封 WAV
    const dataLen = pcm.length * 2
    const header = new ArrayBuffer(44)
    const v = new DataView(header)
    v.setUint32(0, 0x52494646, false)
    v.setUint32(4, 36 + dataLen, true)
    v.setUint32(8, 0x57415645, false)
    v.setUint32(12, 0x666D7420, false)
    v.setUint32(16, 16, true)
    v.setUint16(20, 1, true)
    v.setUint16(22, 1, true)
    v.setUint32(24, targetSr, true)
    v.setUint32(28, targetSr * 2, true)
    v.setUint16(32, 2, true)
    v.setUint16(34, 16, true)
    v.setUint32(36, 0x64617461, false)
    v.setUint32(40, dataLen, true)
    return new Blob([header, pcm.buffer], { type: 'audio/wav' })
  } finally {
    ctx.close().catch(() => {})
  }
}

export function useVoiceInput(opts: VoiceOptions = {}) {
  const state = ref<VoiceState>('idle')
  const durationMs = ref(0)
  const levels = ref<number[]>(new Array(BARS).fill(0.06))
  const errorMsg = ref('')

  let stream: MediaStream | null = null
  let recorder: MediaRecorder | null = null
  let chunks: BlobPart[] = []
  let audioCtx: AudioContext | null = null
  let analyser: AnalyserNode | null = null
  let rafId = 0
  let timer = 0
  let startedAt = 0
  let cancelled = false
  let mime = ''
  let simulated = false

  const maxMs = (opts.maxSeconds ?? 60) * 1000

  function stopMedia() {
    if (rafId) {
      cancelAnimationFrame(rafId)
      rafId = 0
    }
    if (timer) {
      clearInterval(timer)
      timer = 0
    }
    if (stream) {
      stream.getTracks().forEach((t) => t.stop())
      stream = null
    }
    if (audioCtx) {
      audioCtx.close().catch(() => {})
      audioCtx = null
    }
    analyser = null
  }

  function cleanup() {
    stopMedia()
    recorder = null
    chunks = []
  }

  function loop() {
    if (!analyser) return
    const buf = new Uint8Array(analyser.frequencyBinCount)
    analyser.getByteFrequencyData(buf)
    const step = Math.max(1, Math.floor(buf.length / BARS))
    const out: number[] = []
    for (let i = 0; i < BARS; i++) {
      out.push(Math.max(0.06, buf[i * step] / 255))
    }
    levels.value = out
    rafId = requestAnimationFrame(loop)
  }

  async function start() {
    if (state.value !== 'idle') return
    errorMsg.value = ''
    cancelled = false
    simulated = false
    chunks = []
    durationMs.value = 0
    state.value = 'requesting'
    try {
      const supportErr = getRecordingSupportError()
      if (supportErr) throw new Error(supportErr)
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mime = pickMime()
      recorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream)
      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size) chunks.push(e.data)
      }
      // 分片采集，避免极短录音 stop 时 ondataavailable 尚未触发导致空 Blob
      recorder.start(250)

      // 实时波形
      const AC: typeof AudioContext =
        window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      audioCtx = new AC()
      const src = audioCtx.createMediaStreamSource(stream)
      analyser = audioCtx.createAnalyser()
      analyser.fftSize = 64
      src.connect(analyser)

      // 计时（含最长录音保护）
      startedAt = Date.now()
      timer = window.setInterval(() => {
        durationMs.value = Date.now() - startedAt
        if (durationMs.value >= maxMs) stop()
      }, 200)

      state.value = 'recording'
      loop()
    } catch (e: unknown) {
      cleanup()
      if (VOICE_USE_MOCK && VOICE_DEMO_FALLBACK) {
        startSimulated() // 仅 mock 模式：无麦克风 → 演示模拟录音
        return
      }
      const name = (e as { name?: string })?.name
      errorMsg.value =
        name === 'NotAllowedError' || name === 'SecurityError'
          ? '麦克风权限被拒绝'
          : name === 'NotFoundError'
            ? '未检测到麦克风'
            : (e as Error)?.message || '无法录音'
      state.value = 'error'
      window.setTimeout(() => {
        if (state.value === 'error') state.value = 'idle'
      }, 4500)
    }
  }

  // 无麦克风演示：合成波形 + 计时，模拟录音态（停止后由 transcribe 强制走 mock）
  function startSimulated() {
    simulated = true
    startedAt = Date.now()
    durationMs.value = 0
    timer = window.setInterval(() => {
      durationMs.value = Date.now() - startedAt
      if (durationMs.value >= maxMs) stop()
    }, 200)
    const animate = () => {
      const t = Date.now() / 130
      const out: number[] = []
      for (let i = 0; i < BARS; i++) {
        const wave = 0.4 + 0.32 * Math.sin(t + i * 0.55)
        out.push(Math.max(0.08, Math.min(1, wave + Math.random() * 0.22)))
      }
      levels.value = out
      rafId = requestAnimationFrame(animate)
    }
    animate()
    state.value = 'recording'
  }

  function stopRecorder(): Promise<Blob> {
    return new Promise((resolve) => {
      if (!recorder || recorder.state === 'inactive') {
        return resolve(new Blob(chunks, { type: mime || 'audio/webm' }))
      }
      recorder.onstop = () => resolve(new Blob(chunks, { type: mime || 'audio/webm' }))
      try {
        recorder.stop()
      } catch {
        resolve(new Blob(chunks, { type: mime || 'audio/webm' }))
      }
    })
  }

  async function stop(): Promise<string | null> {
    if (state.value !== 'recording') return null
    state.value = 'transcribing'
    const blob = simulated ? new Blob([]) : await stopRecorder()
    stopMedia() // 释放麦克风/波形，保留 state=transcribing
    if (cancelled) {
      state.value = 'idle'
      return null
    }
    if (!simulated && blob.size < 512) {
      errorMsg.value = '录音太短，请按住多说几秒'
      state.value = 'error'
      window.setTimeout(() => {
        if (state.value === 'error') state.value = 'idle'
      }, 4500)
      return null
    }
    try {
      const text = await transcribe(blob)
      const clean = (text || '').trim()
      if (!clean) {
        // 识别成功但无内容（静音/没听清）→ 显式提示，不静默
        errorMsg.value = '未识别到语音，请重试'
        state.value = 'error'
        window.setTimeout(() => {
          if (state.value === 'error') state.value = 'idle'
        }, 2500)
        return null
      }
      state.value = 'idle'
      return clean
    } catch (e: unknown) {
      errorMsg.value = (e as Error)?.message || '识别失败，请重试'
      state.value = 'error'
      window.setTimeout(() => {
        if (state.value === 'error') state.value = 'idle'
      }, 4500)
      return null
    }
  }

  function cancel() {
    if (state.value === 'recording') {
      cancelled = true
      if (simulated) {
        cleanup()
        state.value = 'idle'
      } else {
        stopRecorder().finally(() => {
          cleanup()
          state.value = 'idle'
        })
      }
    } else if (state.value !== 'transcribing') {
      cleanup()
      state.value = 'idle'
    }
  }

  async function transcribe(blob: Blob): Promise<string> {
    if (simulated && !VOICE_USE_MOCK) {
      throw new Error('需要麦克风权限才能使用语音输入')
    }
    if (VOICE_USE_MOCK || simulated) {
      await new Promise((r) => setTimeout(r, 1200))
      const samples =
        opts.mockSamples && opts.mockSamples.length
          ? opts.mockSamples
          : ['（语音示例）帮我看看今天的健康状况。']
      return samples[_mockIdx++ % samples.length]
    }
    // Layer 2：真实千问 ASR。若原始 mime 非 wav，前端转 PCM/WAV
    // （qwen3-omni-flash input_audio 仅可靠支持 wav；webm/opus 需先解码）
    let audioBlob = blob
    let sendMime = mime || blob.type || ''
    const isWebmOrOgg = /webm|opus|ogg|mp4|m4a|aac/i.test(sendMime)
    if (isWebmOrOgg && !/wav/i.test(sendMime)) {
      try {
        audioBlob = await blobToWavBlob(blob)
        sendMime = 'audio/wav'
      } catch {
        // 解码失败则原样上传（让后端试兼容 or 报错）
      }
    }
    const fd = new FormData()
    fd.append('audio', audioBlob, 'voice.wav')
    fd.append('format', sendMime || audioBlob.type || '')
    const resp = await fetch('/api/asr', { method: 'POST', body: fd })
    if (!resp.ok) {
      let msg = '识别失败，请重试'
      try {
        const err = await resp.json()
        const detail = err?.detail
        if (typeof detail === 'string') msg = detail
        else if (detail?.error) msg = detail.error
        else if (err?.error) msg = err.error
      } catch {
        /* ignore */
      }
      throw new Error(msg)
    }
    const data = await resp.json()
    return data.text || ''
  }

  onUnmounted(cleanup)

  return { state, durationMs, levels, errorMsg, start, stop, cancel }
}
