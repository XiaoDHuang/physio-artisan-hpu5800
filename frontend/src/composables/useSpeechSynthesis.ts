/**
 * 语音合成 composable —— 两层设计
 *
 * Layer 1（浏览器降级）：window.speechSynthesis，不需要后端
 * Layer 2（本期主路径）：POST /api/tts → 大模型 TTS → 返回 mp3 Blob → Audio 播放
 *
 * speak(text) 优先走 Layer 2，失败自动降级 Layer 1。
 * 对外接口不变：{ isSpeaking, isLoading, errorMsg, speak, stop }
 */
import { ref, onUnmounted } from 'vue'

export function useSpeechSynthesis() {
  const isSpeaking = ref(false)
  const isLoading = ref(false)
  const errorMsg = ref<string | null>(null)

  let audio: HTMLAudioElement | null = null
  let abortController: AbortController | null = null
  let voicesWarmed = false

  // ==================== Layer 1: 浏览器 TTS（降级） ====================

  function getChineseVoice(): SpeechSynthesisVoice | null {
    const voices = speechSynthesis.getVoices()
    const cn = voices.find((v) => v.lang.startsWith('zh-CN'))
    if (cn) return cn
    const zh = voices.find((v) => v.lang.startsWith('zh'))
    if (zh) return zh
    return null
  }

  function warmVoices() {
    if (voicesWarmed) return
    voicesWarmed = true
    speechSynthesis.getVoices()
    speechSynthesis.onvoiceschanged = () => {
      speechSynthesis.getVoices()
    }
  }

  function speakBrowser(text: string) {
    warmVoices()
    speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(text)
    u.rate = 0.9
    u.volume = 1.0
    const voice = getChineseVoice()
    if (voice) u.voice = voice
    u.onstart = () => { isSpeaking.value = true }
    u.onend = () => { isSpeaking.value = false }
    u.onerror = () => {
      isSpeaking.value = false
      errorMsg.value = '浏览器语音播放异常'
      setTimeout(() => {
        if (errorMsg.value === '浏览器语音播放异常') errorMsg.value = null
      }, 2500)
    }
    speechSynthesis.speak(u)
  }

  function stopBrowser() {
    speechSynthesis.cancel()
    isSpeaking.value = false
  }

  // ==================== Layer 2: 大模型 TTS ====================

  function stopAudio() {
    if (audio) {
      audio.onended = null
      audio.onerror = null
      audio.pause()
      audio.currentTime = 0
      if (audio.src) URL.revokeObjectURL(audio.src)
      audio = null
    }
  }

  async function speakTTS(text: string): Promise<HTMLAudioElement | null> {
    abortController = new AbortController()
    const resp = await fetch('/api/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
      signal: abortController.signal,
    })
    if (!resp.ok) {
      throw new Error(`TTS 服务返回 ${resp.status}`)
    }
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)

    const a = new Audio(url)
    audio = a
    a.onplay = () => { isSpeaking.value = true }
    a.onended = () => {
      isSpeaking.value = false
      URL.revokeObjectURL(url)
      audio = null
    }
    a.onerror = () => {
      isSpeaking.value = false
      URL.revokeObjectURL(url)
      audio = null
    }
    try {
      await a.play()
      return a
    } catch {
      URL.revokeObjectURL(url)
      audio = null
      return null
    }
  }

  // ==================== 对外接口 ====================

  async function speak(text: string) {
    stop()

    isLoading.value = true
    errorMsg.value = null
    try {
      const a = await speakTTS(text)
      isLoading.value = false
      if (!a) {
        speakBrowser(text)
      }
    } catch (e: any) {
      isLoading.value = false
      if (e?.name === 'AbortError') return
      speakBrowser(text)
    }
  }

  function stop() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
    stopAudio()
    stopBrowser()
    isSpeaking.value = false
    isLoading.value = false
  }

  onUnmounted(() => { stop() })

  return { isSpeaking, isLoading, errorMsg, speak, stop }
}
