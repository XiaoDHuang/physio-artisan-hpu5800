## 📋 目录

1. [项目概述](#项目概述)
2. [系统架构](#系统架构)
3. [核心算法模块](#核心算法模块)
4. [AI多模型路由架构](#ai多模型路由架构)
5. [Agent工作流](#agent工作流)
6. [数据流向图](#数据流向图)
7. [技术栈](#技术栈)
8. [快速开始](#快速开始)

---

## 1. 项目概述

### 1.1 项目目标

HPU（Health Personal Unit）是一个基于大语言模型的**自主智能体系统**，专注于健身、饮食和睡眠的综合健康管理。

**核心特性：**
- 多Agent协同工作，基于LangGraph状态机
- 多模态输入（手表数据、视频、图片）
- 多模态输出（图表、语音报告）
- 嵌入式算法本地计算，无需依赖AI API
- 灵活的多AI模型路由支持

### 1.2 功能模块

| 模块 | 功能描述 |
|------|---------|
| 生理数据看板 | 手表JSON数据上传，身体年龄评估，雷达图展示 |
| 视觉工坊 | MediaPipe骨骼分析，食物图片营养识别 |
| 智能体会诊厅 | 多Agent状态机可视化，Function Calling日志 |
| AI对话 | 支持图片/视频上传，实时调用链展示 |

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         Streamlit 前端                            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │  首页   │  │ 生理看板 │  │ 视觉工坊 │  │ AI对话  │           │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘           │
└───────┼─────────────┼─────────────┼─────────────┼────────────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AI Provider Manager                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │ OpenAI  │  │ 智谱AI  │  │ Claude  │  │ 自定义  │           │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Agent Orchestration                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │ StateEval   │───▶│ Exercise    │───▶│ Nutrition   │         │
│  │ (评估Agent) │    │ Coach       │    │ Planner     │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                                    │                   │
│         └──────────────┬─────────────────────┘                   │
│                        ▼                                         │
│              ┌─────────────────┐                                 │
│              │ Guardrail       │                                 │
│              │ Auditor (安全)  │                                 │
│              └─────────────────┘                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    嵌入式算法模块 (Python)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ 身体指标    │  │ 睡眠分析    │  │ 姿态分析    │             │
│  │ 计算器      │  │  Sleep      │  │   Pose      │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         PostgreSQL 数据库                         │
│  users | watch_data | exercise_records | nutrition_logs          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```
HPU/
├── app.py                      # Streamlit主入口
├── pages/                      # 页面模块
│   ├── 1_physiological_dashboard.py   # 生理数据看板
│   ├── 2_vision_lab.py               # 视觉多模态工坊
│   ├── 3_agent_arena.py              # 智能体会诊厅
│   ├── 4_chat_agent.py               # AI对话界面
│   └── settings_page.py               # 设置页面
├── src/
│   ├── agent/                 # Agent模块
│   │   ├── __init__.py
│   │   ├── state.py          # Agent状态定义
│   │   ├── multi_agent.py    # 多Agent编排
│   │   └── hpu_agent.py      # 主Agent
│   ├── ai/                    # AI模块
│   │   ├── __init__.py
│   │   ├── provider_manager.py    # 多API路由管理
│   │   └── prompt_engine.py      # 提示词引擎
│   ├── tools/                 # 工具模块 (嵌入式算法)
│   │   ├── __init__.py
│   │   ├── calculator.py     # 身体指标计算器
│   │   ├── sleep.py          # 睡眠分析器
│   │   ├── nutrition.py       # 营养分析器
│   │   └── training.py        # 训练计划生成
│   ├── vision/                # 视觉分析模块
│   │   ├── __init__.py
│   │   └── pose_analyzer.py   # MediaPipe姿态分析
│   ├── safety/                # 安全模块
│   │   ├── __init__.py
│   │   └── guardrails.py     # 安全过滤
│   ├── multimodal/            # 多模态输出
│   │   ├── __init__.py
│   │   ├── chart_generator.py # 图表生成
│   │   └── speech.py          # 语音合成
│   ├── database/              # 数据库模块
│   │   ├── __init__.py
│   │   ├── models.py          # 数据模型
│   │   └── postgres.py        # PostgreSQL连接
│   └── utils/                 # 工具函数
├── sql/                       # SQL脚本
│   └── init_hpu.sql
├── .env                       # 环境变量配置
├── requirements.txt            # Python依赖
└── README.md                   # 项目文档
```

---

## 3. 核心算法模块

### 3.1 身体指标计算器 (`src/tools/calculator.py`)

**类名**: `BodyMetricsCalculator`

**核心算法**:

#### 3.1.1 BMI计算
```
BMI = 体重(kg) / 身高(m)²

分类标准:
- < 18.5: 偏瘦
- 18.5-24: 正常
- 24-28: 超重
- > 28: 肥胖
```

#### 3.1.2 BMR (基础代谢率) - Mifflin-St Jeor公式
```
男性: BMR = 10×体重 + 6.25×身高 - 5×年龄 + 5
女性: BMR = 10×体重 + 6.25×身高 - 5×年龄 - 161
```

#### 3.1.3 TDEE (每日总能量消耗)
```
TDEE = BMR × 活动系数

活动系数:
- 久坐: 1.2
- 轻度活跃: 1.375
- 中度活跃: 1.55
- 非常活跃: 1.725
- 极度活跃: 1.9
```

#### 3.1.4 身体年龄估算算法
```python
def calculate_body_age(resting_hr, bmi, exercise_freq, sleep_quality):
    base_age = 30
    
    # 心率评分 (越低越好)
    if hr < 60: hr_score = -5    # 运动员
    elif hr < 70: hr_score = -3
    elif hr < 80: hr_score = 0
    elif hr < 90: hr_score = 3
    else: hr_score = 5
    
    # BMI评分
    if 18.5 <= bmi < 24: bmi_score = 0
    elif 24 <= bmi < 28: bmi_score = 3
    else: bmi_score = 6
    
    # 运动频率评分
    if freq >= 5: exercise_score = -5
    elif freq >= 3: exercise_score = -3
    else: exercise_score = 3
    
    # 睡眠评分
    if sleep_quality >= 8: sleep_score = -2
    elif sleep_quality >= 6: sleep_score = 0
    else: sleep_score = 3
    
    estimated_age = base_age + hr_score + bmi_score + exercise_score + sleep_score
    return max(18, min(80, estimated_age))
```

#### 3.1.5 宏量营养素计算
```python
def calculate_macro_needs(tdee, goal):
    if goal == "lose_weight": target = tdee * 0.8
    elif goal == "gain_muscle": target = tdee * 1.1
    else: target = tdee
    
    protein = (target * 0.30) / 4   # 蛋白质4kcal/g
    carbs = (target * 0.40) / 4     # 碳水4kcal/g
    fat = (target * 0.30) / 9       # 脂肪9kcal/g
    return {"protein": protein, "carbs": carbs, "fat": fat}
```

---

### 3.2 睡眠分析器 (`src/tools/sleep.py`)

**类名**: `SleepAnalyzer`

**核心算法**:

#### 3.2.1 睡眠阶段比例
```
正常睡眠结构:
- 深睡眠: 15-25%
- REM睡眠: 20-25%
- 浅睡眠: 45-55%
```

#### 3.2.2 综合睡眠评分
```python
def calculate_overall_score(hours, deep_percent, quality):
    # 各维度权重
    duration_weight = 0.4
    deep_weight = 0.3
    quality_weight = 0.3
    
    # 时长评分 (7-9小时满分)
    if 7 <= hours <= 9: duration_score = 100
    else: duration_score = (hours / 7) * 100
    
    # 深睡眠评分 (15-25%满分)
    if 15 <= deep_percent <= 25: deep_score = 100
    else: deep_score = (deep_percent / 15) * 100
    
    # 质量评分 (1-10 → 百分制)
    quality_score = quality * 10
    
    overall = (duration_score * duration_weight +
               deep_score * deep_weight +
               quality_score * quality_weight)
    
    # 等级判定
    if overall >= 90: grade = "A 优秀"
    elif overall >= 80: grade = "B 良好"
    elif overall >= 70: grade = "C 一般"
    else: grade = "D 较差"
    
    return {"score": overall, "grade": grade}
```

---

### 3.3 姿态分析器 (`src/vision/pose_analyzer.py`)

**类名**: `PoseAnalyzer`

**技术**: MediaPipe Pose + OpenCV

**核心算法**:

#### 3.3.1 骨骼关键点 (33点)
```
头部: 0-10 (鼻、眼、耳、口)
躯干: 11-24 (肩、髋)
四肢: 25-32 (膝、踝、足)
```

#### 3.3.2 深蹲角度计算
```python
def calculate_squat_angles(landmarks):
    # 躯干角度 (肩-髋与垂直线夹角)
    trunk_angle = arctan((shoulder.x - hip.x) / (hip.y - shoulder.y))
    
    # 髋角 (肩-髋-膝三点角)
    hip_angle = angle(shoulder, hip, knee)
    
    # 膝角 (髋-膝-踝三点角)
    knee_angle = angle(hip, knee, ankle)
    
    return {"trunk": trunk_angle, "hip": hip_angle, "knee": knee_angle}
```

#### 3.3.3 动作质量评估
```python
SQUAT_THRESHOLDS = {
    "knee_ideal_min": 85,
    "knee_ideal_max": 95,
    "trunk_warning": 70,  # 超过此值=塌腰
    "hip_ideal_min": 70,
    "hip_ideal_max": 100
}

def assess_squat_form(angles):
    issues = 0
    
    # 塌腰检测
    if angles.trunk_angle > 70:
        warnings.append("核心塌腰警告!")
        issues += 2  # 塌腰是严重问题
    
    # 膝盖前移检测
    if angles.knee_angle > 100:
        warnings.append("膝盖过度前移")
        issues += 1
    
    # 质量等级
    if issues == 0: return "excellent"
    elif issues == 1: return "good"
    elif issues <= 2: return "fair"
    else: return "poor"
```

---

## 4. AI多模型路由架构

### 4.1 Provider管理器

```
AIProviderManager
├── OpenAIProvider      (GPT-4, GPT-4-Turbo, GPT-3.5)
├── ZhipuProvider       (GLM-4, GLM-4V)
├── AnthropicProvider   (Claude-3-Opus, Claude-3-Sonnet)
├── AzureProvider       (Azure OpenAI)
├── CustomProvider      (支持任意OpenAI兼容API)
└── MockProvider        (测试用)
```

### 4.2 Agent-Provider绑定

| Agent | 默认Provider | 建议模型 | 用途 |
|-------|-------------|---------|------|
| HPUAssistant | OpenAI | GPT-4 | 主对话协调 |
| StateEvaluator | 智谱AI | GLM-4 | 状态评估计算 |
| ExerciseCoach | OpenAI | GPT-4-Turbo | 训练计划 |
| NutritionPlanner | 智谱AI | GLM-4 | 营养分析 |
| GuardrailAuditor | Claude | Claude-3-Opus | 安全审核 |

### 4.3 自定义API配置

支持添加自定义AI服务：
- 名称: 自定义名称
- API密钥: 服务商提供的密钥
- 端点: API地址 (如 `https://api.siliconflow.cn/v1`)
- 模型列表: 支持的模型 (逗号分隔)

**支持的代理**: HTTP/HTTPS代理配置

---

## 5. Agent工作流

### 5.1 LangGraph状态机

```
┌──────────────┐
│    START     │
└──────┬───────┘
       ▼
┌──────────────┐
│  用户输入    │◀──────────────┐
└──────┬───────┘              │
       ▼                      │
┌──────────────┐             │
│ 输入安全检查  │             │
│ (Guardrail)  │──违规──▶ [拒绝响应]
└──────┬───────┘             │
       ▼                      │
┌──────────────┐             │
│  状态评估    │             │
│StateEvaluator│             │
│ (嵌入式算法) │             │
└──────┬───────┘             │
       ▼                      │
┌──────────────┐             │
│  训练教练    │             │
│ExerciseCoach │             │
└──────┬───────┘             │
       ▼                      │
┌──────────────┐             │
│  营养规划    │             │
│NutritionPlan │             │
└──────┬───────┘             │
       ▼                      │
┌──────────────┐             │
│ 输出安全审核  │             │
│ (Guardrail)  │             │
└──────┬───────┘             │
       ▼                      │
┌──────────────┐             │
│  多模态输出  │──────────────┘
│ (图表+语音)  │
└──────────────┘
```

### 5.2 函数调用 (Function Calling)

**可调用的工具**:

1. **calculate_body_metrics** - 计算BMI/BMR/TDEE
2. **analyze_sleep** - 睡眠质量分析
3. **analyze_pose** - 姿态角度分析
4. **generate_training_plan** - 生成训练计划
5. **calculate_nutrition** - 计算营养需求
6. **speak_report** - 语音播报

---

## 6. 数据流向图

### 6.1 用户输入 → AI分析 → 多模态输出

```
                    ┌─────────────────────────────────────────────┐
                    │              用户输入层                      │
                    │  ┌─────────┐ ┌─────────┐ ┌─────────┐     │
                    │  │ 手表JSON │ │ 运动视频 │ │ 食物图片 │     │
                    │  └────┬────┘ └────┬────┘ └────┬────┘     │
                    └───────┼──────────┼──────────┼──────────────┘
                            │          │          │
                            ▼          │          │
                    ┌───────────────┐ │          │
                    │  数据解析层    │ │          │
                    │  JSON解析     │◀┘          │
                    │  MediaPipe    │            │
                    └───────┬───────┘            │
                            │                    │
                            ▼                    │
                    ┌───────────────────────────────────────┐
                    │            嵌入式算法层                 │
                    │  ┌──────────┐ ┌──────────┐ ┌────────┐ │
                    │  │ 身体年龄  │ │ 睡眠质量  │ │ 姿态   │ │
                    │  │ 评估     │ │ 评估     │ │ 分析   │ │
                    │  │ (Python) │ │ (Python) │ │(MediaPipe)│
                    │  └──────────┘ └──────────┘ └────────┘ │
                    └───────────────────┬───────────────────────┘
                                        │
                                        ▼
                    ┌───────────────────────────────────────┐
                    │            AI决策层                     │
                    │        LangGraph Agent                  │
                    │  ┌─────────┐ ┌─────────┐ ┌─────────┐  │
                    │  │ 状态评估 │ │ 训练计划 │ │ 营养规划 │  │
                    │  └────┬────┘ └────┬────┘ └────┬────┘  │
                    │       └────────────┴────────────┘       │
                    │                   │                     │
                    │              ┌────┴────┐               │
                    │              │ 安全审核 │               │
                    │              └─────────┘               │
                    └───────────────────┬───────────────────────┘
                                        │
                                        ▼
                    ┌───────────────────────────────────────┐
                    │            多模态输出层                 │
                    │  ┌─────────┐ ┌─────────┐ ┌─────────┐  │
                    │  │ 雷达图  │ │ 趋势图  │ │ 骨骼图  │  │
                    │  │(Matplotlib)│ │(Matplotlib)│ │(OpenCV)│  │
                    │  └─────────┘ └─────────┘ └─────────┘  │
                    │  ┌─────────┐                          │
                    │  │ 语音报告 │                          │
                    │  │(Edge-TTS)│                         │
                    │  └─────────┘                          │
                    └───────────────────────────────────────┘
```

---

## 7. 技术栈

### 7.1 核心技术

| 类别 | 技术 | 用途 |
|------|------|------|
| 前端 | Streamlit | 多页面Web应用 |
| 编排 | LangGraph | 多Agent状态机 |
| 视觉 | MediaPipe | 骨骼关键点提取 |
| 视觉 | OpenCV | 图像处理 |
| 语音 | Edge-TTS | 神经网络语音合成 |
| 数据库 | PostgreSQL | 数据持久化 |
| 可视化 | Matplotlib | 图表生成 |

### 7.2 AI集成

| Provider | 用途 | 模型 |
|----------|------|------|
| OpenAI | 主对话、训练计划 | GPT-4, GPT-4-Turbo |
| 智谱AI | 状态评估、营养规划 | GLM-4, GLM-4V |
| Anthropic | 安全审核 | Claude-3-Opus |
| 自定义 | 支持任意兼容API | 用户配置 |

---

## 8. 快速开始

### 8.0 安装 Python

本项目推荐使用 **Python 3.10 或更高版本**。

#### 方法一：官网下载（推荐）

1. 访问 https://www.python.org/downloads/windows/
2. 下载最新的 Python 3.12 安装包（`.exe` installer）
3. 运行安装程序，**务必勾选** "Add Python to PATH"（添加到环境变量）
4. 点击 "Install Now"

安装完成后，打开 PowerShell 验证：

```powershell
python --version
pip --version
```

#### 方法二：Microsoft Store

打开 Microsoft Store，搜索 "Python"，选择 Python 3.12 或 3.11，点击安装。会自动配置好 PATH。

#### 方法三：使用 pyenv 管理多版本

如果你需要同时管理多个 Python 版本，可以用 pyenv-win：

```powershell
# 使用 PowerShell 安装 pyenv
iwr https://pyenv.run | Invoke-Expression

# 安装 Python 3.12
pyenv install 3.12.0

# 全局使用
pyenv global 3.12.0
```

> **建议：** 简单使用选方法一或二；如果你会用到这台机器做多个 Python 项目（不同版本），方法三更方便。

### 8.1 安装依赖

```bash
pip install -r requirements.txt
```

### 8.2 配置环境变量

编辑 `.env` 文件:
```env
# 数据库
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=hpu_db
PG_USER=postgres
PG_PASSWORD=your_password

# AI API (可选)
OPENAI_API_KEY=sk-...
ZHIPU_API_KEY=...

# 代理 (可选)
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

### 8.3 初始化数据库

```bash
# 创建数据库
psql -U postgres -d postgres -f backend/sql/hpu_db.sql
```

### 8.4 启动应用

> **常见问题：** 如果提示 "无法识别 'streamlit'"，请先执行 `pip install -r requirements.txt` 安装依赖。

```bash
streamlit run app.py
```

启动后访问 http://localhost:8501

---

**作者**: HPU团队
**版本**: 1.0.0
**最后更新**: 2026-06-01
