// 与 backend FastAPI 对接的类型定义（详见 docs/接口契约.md）

// ---------- /chat 结构化响应 ----------
export type ChatIntent = 'report' | 'data_entry' | 'other' | 'blocked'

export interface ChatResponse {
  conversation_id: string
  intent: ChatIntent
  data_type: string | null
  reply: string
  extracted: Record<string, unknown>
  missing: string[]
  can_proceed: boolean
  saved: boolean
  task_id: string | null
}

// ---------- /dashboard 看板 ----------
export interface DashboardKpi {
  health_score: number | null
  score_delta_vs_last_week: number | null
  status: string
  exercise_rate: number | null
  exercise_rate_delta: number | null
  risk: string
}

export interface BodyOverview {
  heart_rate: number | null
  weight_kg: number | null
  bmi: number | null
  bmr: number | null
  body_fat_pct: number | null
  muscle_mass_kg: number | null
  update_date: string | null
}

export interface SleepStage {
  hour: number
  deep: number
  light: number
  rem: number
  awake: number
}
export interface SleepPanel {
  score: number | null
  total_hours: number | null
  deep_sleep_percent: number | null
  rem_sleep_percent: number | null
  stages_timeline: SleepStage[]
}
export interface NutritionPanel {
  total_calories: number | null
  protein_g: number | null
  carbs_g: number | null
  fat_g: number | null
  ratios: { protein?: number; carbs?: number; fat?: number }
  balance_score: number | null
}
export interface ExerciseTodayPanel {
  steps: number | null
  steps_goal: number | null
  duration_minutes: number | null
  calories_burned: number | null
  intensity: string
}
export interface WeekSummary {
  workout_days: number | null
  days_goal: number | null
  total_calories_burned: number | null
  avg_steps: number | null
  avg_sleep: number | null
}
export interface HealthAdvice {
  exercise: string
  sleep: string
  nutrition: string
}

export interface Dashboard {
  kpi: DashboardKpi
  body_overview: BodyOverview
  sleep: SleepPanel
  nutrition: NutritionPanel
  exercise_today: ExerciseTodayPanel
  week_summary: WeekSummary
  goals: Record<string, unknown>
}

export interface DashboardResponse {
  user_id: number
  dashboard: Dashboard
}

// ---------- /report/latest 报告结果（本期只取 final_report.chart_data.dashboard）----------
export interface ReportResult {
  success: boolean
  source?: string
  mode?: string
  fatigue_level?: string
  final_report?: {
    visual_metrics?: Record<string, unknown>
    vocal_narrative?: string
    chart_data?: {
      dashboard?: Dashboard
      [k: string]: unknown
    }
  }
  [k: string]: unknown
}
