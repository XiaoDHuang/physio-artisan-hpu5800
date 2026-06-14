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

// ---------- /exercise 运动分析页 ----------
export type SourceMap = Record<string, 'db' | 'mock' | 'derived' | 'default'>

export interface ExerciseTodayOverview {
  steps: number | null
  calories_burned: number | null
  duration_minutes: number | null
  intensity: string
  steps_goal: number | null
  duration_goal: number | null
  calories_goal: number | null
}
export interface ExerciseTodayStatus {
  diet: { status: string; intake: number | null; goal: number | null }
  sleep: { status: string; hours: number | null }
  fatigue: { level: string; advice: string }
}
export interface ExerciseRecord {
  exercise_type: string
  duration_minutes: number | null
  calories: number | null
  time_range: string | null
  distance_km: number | null
}
export interface WeekTrendPoint {
  date: string
  steps: number | null
}
export interface ExerciseAdvice {
  exercise: string
  nutrition: string
  sleep: string
}
export interface ExerciseAchievement {
  percentile: number | null
  description: string
}
export interface ExercisePage {
  today_overview: ExerciseTodayOverview
  today_status: ExerciseTodayStatus
  today_records: ExerciseRecord[]
  week_trend: WeekTrendPoint[]
  advice: ExerciseAdvice
  achievement: ExerciseAchievement
}
export interface ExerciseResponse {
  user_id: number
  exercise: ExercisePage
  sources: SourceMap
}

// ---------- /sleep 睡眠监测页 ----------
export interface SleepToday {
  sleep_score: number | null
  grade: string
  total_hours: number | null
  deep_sleep_hours: number | null
  nap_minutes: number | null
  bedtime: string | null
  wake_time: string | null
}
export interface SleepRangeInfo {
  status: string
  recommend_min: number | null
  recommend_max: number | null
}
export interface SleepTrendPoint {
  date: string
  total_hours: number | null
  sleep_score: number | null
}
export interface SleepAdvice {
  sleep: string
  nutrition: string
  exercise: string
}
export interface SleepFoods {
  recommended: string[]
  avoid: string[]
}
export interface SleepPage {
  today: SleepToday
  duration: SleepRangeInfo
  nap: SleepRangeInfo
  trend: SleepTrendPoint[]
  advice: SleepAdvice
  foods: SleepFoods
}
export interface SleepResponse {
  user_id: number
  sleep: SleepPage
  sources: SourceMap
}
export interface SleepEntryPayload {
  bedtime: string
  wake_time: string
  nap_minutes?: number | null
  on_date?: string | null
  user_id?: number
}
export interface SleepEntryResult {
  saved: boolean
  sleep_data: Record<string, unknown>
}

// ---------- /nutrition 饮食管理页 ----------
export interface NutritionKpi {
  goal_calories: number | null
  intake_calories: number | null
  remaining_calories: number | null
  achievement_rate: number | null
}
export interface MacroItem {
  grams: number | null
  calories: number | null
  percent: number | null
}
export interface NutritionEnergy {
  total_calories: number | null
  macros: { carbs: MacroItem; protein: MacroItem; fat: MacroItem }
  recommended_calories: number | null
  bmr: number | null
  exercise_burn: number | null
  energy_gap: number | null
}
export interface MealFood {
  name: string
  grams: number | null
  calories: number | null
}
export interface Meal {
  meal_type: string
  time: string
  total_calories: number | null
  foods: MealFood[]
}
export interface NutritionExerciseItem {
  name: string
  sets?: number | null
  reps?: number | null
  duration?: string | null
}
export interface NutritionExerciseAdvice {
  training_type: string
  duration: string
  calorie_target: number | null
  exercises: NutritionExerciseItem[]
}
export interface NutritionPage {
  kpi: NutritionKpi
  energy: NutritionEnergy
  meals: Meal[]
  exercise_advice: NutritionExerciseAdvice
}
export interface NutritionResponse {
  user_id: number
  date: string
  nutrition: NutritionPage
  sources: SourceMap
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
