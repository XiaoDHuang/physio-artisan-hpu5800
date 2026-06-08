"""
训练模板库
提供各类训练计划和模板
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Exercise:
    """单个训练动作"""
    name: str
    sets: int
    reps: str  # 可以是 "8-12" 或 "30秒"
    rest_seconds: int
    muscle_group: str
    equipment: str = "无"


@dataclass
class WorkoutDay:
    """单日训练"""
    day_name: str
    focus: str
    exercises: List[Exercise]
    duration_minutes: int
    intensity: str  # "low", "medium", "high"
    calories_estimate: int


class TrainingTemplates:
    """训练模板库"""
    
    # 训练模板定义
    TEMPLATES = {
        "beginner": {
            "lose_weight": [
                {
                    "day": "Day 1 - 全身训练",
                    "focus": "全身激活",
                    "exercises": [
                        {"name": "深蹲", "sets": 3, "reps": "12", "rest": 60, "muscle": "下肢"},
                        {"name": "俯卧撑", "sets": 3, "reps": "8-10", "rest": 60, "muscle": "胸肩"},
                        {"name": "平板支撑", "sets": 3, "reps": "30秒", "rest": 45, "muscle": "核心"},
                        {"name": "哑铃划船", "sets": 3, "reps": "12", "rest": 60, "muscle": "背部"},
                        {"name": "快走/慢跑", "sets": 1, "reps": "20分钟", "rest": 0, "muscle": "心肺"}
                    ],
                    "duration": 45,
                    "intensity": "medium",
                    "calories": 280
                },
                {
                    "day": "Day 2 - 有氧+核心",
                    "focus": "燃脂+核心",
                    "exercises": [
                        {"name": "开合跳", "sets": 3, "reps": "30秒", "rest": 30, "muscle": "全身"},
                        {"name": "登山者", "sets": 3, "reps": "20秒", "rest": 30, "muscle": "核心"},
                        {"name": "波比跳", "sets": 3, "reps": "8", "rest": 60, "muscle": "全身"},
                        {"name": "卷腹", "sets": 3, "reps": "15", "rest": 30, "muscle": "腹肌"},
                        {"name": "骑车/椭圆机", "sets": 1, "reps": "25分钟", "rest": 0, "muscle": "心肺"}
                    ],
                    "duration": 50,
                    "intensity": "high",
                    "calories": 350
                },
                {
                    "day": "Day 3 - 休息/轻松活动",
                    "focus": "恢复",
                    "exercises": [
                        {"name": "散步", "sets": 1, "reps": "30分钟", "rest": 0, "muscle": "放松"},
                        {"name": "拉伸", "sets": 1, "reps": "15分钟", "rest": 0, "muscle": "柔韧"}
                    ],
                    "duration": 45,
                    "intensity": "low",
                    "calories": 100
                }
            ],
            "gain_muscle": [
                {
                    "day": "Day 1 - 推（胸肩三头）",
                    "focus": "推力肌群",
                    "exercises": [
                        {"name": "卧推", "sets": 4, "reps": "8-10", "rest": 90, "muscle": "胸"},
                        {"name": "哑铃肩推", "sets": 3, "reps": "10", "rest": 60, "muscle": "肩"},
                        {"name": "绳索下压", "sets": 3, "reps": "12", "rest": 60, "muscle": "三头"},
                        {"name": "侧平举", "sets": 3, "reps": "12", "rest": 45, "muscle": "肩"}
                    ],
                    "duration": 55,
                    "intensity": "medium",
                    "calories": 220
                },
                {
                    "day": "Day 2 - 拉（背二头）",
                    "focus": "拉力肌群",
                    "exercises": [
                        {"name": "引体向上", "sets": 4, "reps": "6-8", "rest": 90, "muscle": "背"},
                        {"name": "杠铃划船", "sets": 4, "reps": "8", "rest": 90, "muscle": "背"},
                        {"name": "哑铃弯举", "sets": 3, "reps": "12", "rest": 60, "muscle": "二头"},
                        {"name": "面拉", "sets": 3, "reps": "15", "rest": 45, "muscle": "后肩"}
                    ],
                    "duration": 55,
                    "intensity": "medium",
                    "calories": 250
                },
                {
                    "day": "Day 3 - 腿",
                    "focus": "下肢",
                    "exercises": [
                        {"name": "深蹲", "sets": 4, "reps": "8-10", "rest": 120, "muscle": "腿"},
                        {"name": "罗马尼亚硬拉", "sets": 4, "reps": "10", "rest": 90, "muscle": "腿"},
                        {"name": "腿举", "sets": 3, "reps": "12", "rest": 90, "muscle": "腿"},
                        {"name": "小腿提踵", "sets": 4, "reps": "15", "rest": 60, "muscle": "小腿"}
                    ],
                    "duration": 60,
                    "intensity": "high",
                    "calories": 300
                }
            ]
        },
        "intermediate": {
            "lose_weight": [
                {
                    "day": "Day 1 - HIIT + 力量",
                    "focus": "燃脂",
                    "exercises": [
                        {"name": "热身 - 跳绳", "sets": 1, "reps": "5分钟", "rest": 0, "muscle": "热身"},
                        {"name": "深蹲跳", "sets": 4, "reps": "12", "rest": 30, "muscle": "下肢"},
                        {"name": "波比跳", "sets": 4, "reps": "10", "rest": 30, "muscle": "全身"},
                        {"name": "俯卧撑", "sets": 4, "reps": "12", "rest": 30, "muscle": "胸"},
                        {"name": "冲刺跑", "sets": 8, "reps": "30秒", "rest": 30, "muscle": "心肺"}
                    ],
                    "duration": 40,
                    "intensity": "high",
                    "calories": 400
                },
                {
                    "day": "Day 2 - 力量训练",
                    "focus": "肌肉保持",
                    "exercises": [
                        {"name": "硬拉", "sets": 4, "reps": "6", "rest": 120, "muscle": "后链"},
                        {"name": "哑铃推举", "sets": 4, "reps": "10", "rest": 90, "muscle": "肩"},
                        {"name": "弓步蹲", "sets": 3, "reps": "12", "rest": 60, "muscle": "腿"},
                        {"name": "TRX划船", "sets": 3, "reps": "12", "rest": 60, "muscle": "背"},
                        {"name": "平板支撑", "sets": 3, "reps": "45秒", "rest": 30, "muscle": "核心"}
                    ],
                    "duration": 55,
                    "intensity": "high",
                    "calories": 320
                },
                {
                    "day": "Day 3 - 有氧稳定",
                    "focus": "心肺耐力",
                    "exercises": [
                        {"name": "慢跑", "sets": 1, "reps": "30分钟", "rest": 0, "muscle": "心肺"},
                        {"name": "核心训练", "sets": 3, "reps": "15分钟", "rest": 0, "muscle": "核心"}
                    ],
                    "duration": 50,
                    "intensity": "medium",
                    "calories": 350
                }
            ],
            "gain_muscle": [
                {
                    "day": "Day 1 - 胸+三头",
                    "focus": "推力",
                    "exercises": [
                        {"name": "平板卧推", "sets": 4, "reps": "6-8", "rest": 120, "muscle": "胸"},
                        {"name": "上斜哑铃推", "sets": 4, "reps": "8", "rest": 90, "muscle": "胸"},
                        {"name": "绳索飞鸟", "sets": 3, "reps": "12", "rest": 60, "muscle": "胸"},
                        {"name": "过头臂屈伸", "sets": 3, "reps": "12", "rest": 60, "muscle": "三头"},
                        {"name": "下压", "sets": 3, "reps": "15", "rest": 60, "muscle": "三头"}
                    ],
                    "duration": 60,
                    "intensity": "high",
                    "calories": 280
                },
                {
                    "day": "Day 2 - 背+二头",
                    "focus": "拉力",
                    "exercises": [
                        {"name": "硬拉", "sets": 4, "reps": "5", "rest": 180, "muscle": "背"},
                        {"name": "引体向上", "sets": 4, "reps": "8", "rest": 90, "muscle": "背"},
                        {"name": "单臂哑铃划船", "sets": 4, "reps": "10", "rest": 60, "muscle": "背"},
                        {"name": "杠铃弯举", "sets": 3, "reps": "10", "rest": 60, "muscle": "二头"},
                        {"name": "锤式弯举", "sets": 3, "reps": "12", "rest": 45, "muscle": "二头"}
                    ],
                    "duration": 65,
                    "intensity": "high",
                    "calories": 300
                },
                {
                    "day": "Day 3 - 腿+肩",
                    "focus": "下肢+推力",
                    "exercises": [
                        {"name": "深蹲", "sets": 5, "reps": "5", "rest": 180, "muscle": "腿"},
                        {"name": "腿举", "sets": 4, "reps": "10", "rest": 90, "muscle": "腿"},
                        {"name": "腿弯举", "sets": 3, "reps": "12", "rest": 60, "muscle": "腿"},
                        {"name": "哑铃侧平举", "sets": 4, "reps": "12", "rest": 45, "muscle": "肩"},
                        {"name": "面拉", "sets": 3, "reps": "15", "rest": 45, "muscle": "后肩"}
                    ],
                    "duration": 70,
                    "intensity": "high",
                    "calories": 350
                }
            ]
        },
        "advanced": {
            "lose_weight": [
                {
                    "day": "Day 1 - 力量+HIIT",
                    "focus": "最大燃脂",
                    "exercises": [
                        {"name": "热身", "sets": 1, "reps": "10分钟", "rest": 0, "muscle": "热身"},
                        {"name": "深蹲大重量", "sets": 5, "reps": "3", "rest": 180, "muscle": "腿"},
                        {"name": "硬拉", "sets": 5, "reps": "3", "rest": 180, "muscle": "后链"},
                        {"name": "HIIT冲刺", "sets": 10, "reps": "20秒", "rest": 40, "muscle": "心肺"}
                    ],
                    "duration": 60,
                    "intensity": "very_high",
                    "calories": 500
                },
                {
                    "day": "Day 2 - 上肢推",
                    "focus": "推力强化",
                    "exercises": [
                        {"name": "卧推", "sets": 5, "reps": "5", "rest": 150, "muscle": "胸"},
                        {"name": "实力举", "sets": 5, "reps": "5", "rest": 150, "muscle": "肩"},
                        {"name": "双杠臂屈伸", "sets": 3, "reps": "8-10", "rest": 90, "muscle": "胸"},
                        {"name": "递减组训练", "sets": 4, "reps": "力竭", "rest": 60, "muscle": "三头"}
                    ],
                    "duration": 65,
                    "intensity": "very_high",
                    "calories": 400
                }
            ],
            "gain_muscle": [
                {
                    "day": "Day 1 - 胸背超级组",
                    "focus": "复合训练",
                    "exercises": [
                        {"name": "平板卧推", "sets": 5, "reps": "5", "rest": 120, "muscle": "胸"},
                        {"name": "引体向上", "sets": 5, "reps": "6-8", "rest": 120, "muscle": "背"},
                        {"name": "上斜卧推", "sets": 4, "reps": "8", "rest": 90, "muscle": "胸"},
                        {"name": "杠铃划船", "sets": 4, "reps": "8", "rest": 90, "muscle": "背"},
                        {"name": "飞鸟", "sets": 4, "reps": "12", "rest": 60, "muscle": "胸"}
                    ],
                    "duration": 75,
                    "intensity": "very_high",
                    "calories": 380
                }
            ]
        }
    }
    
    # 训练动作库
    EXERCISE_LIBRARY = {
        "胸部": ["卧推", "上斜卧推", "下斜卧推", "哑铃飞鸟", "俯卧撑", "双杠臂屈伸", "绳索飞鸟"],
        "背部": ["引体向上", "高位下拉", "杠铃划船", "哑铃划船", "坐姿划船", "直臂下压"],
        "肩部": ["实力举", "哑铃肩推", "侧平举", "前平举", "面拉", "俯身飞鸟"],
        "手臂": ["杠铃弯举", "哑铃弯举", "锤式弯举", "过头臂屈伸", "下压", "集中弯举"],
        "腿部": ["深蹲", "硬拉", "腿举", "弓步蹲", "腿弯举", "腿伸展", "小腿提踵"],
        "核心": ["平板支撑", "卷腹", "俄罗斯转体", "登山者", "死虫", "悬垂举腿"],
        "有氧": ["跑步", "骑车", "椭圆机", "跳绳", "游泳", "HIIT"]
    }
    
    def __init__(self):
        self.templates = self.TEMPLATES
        self.exercise_library = self.EXERCISE_LIBRARY
    
    def get_template(
        self,
        fitness_level: str,
        goal: str
    ) -> List[Dict]:
        """
        获取训练模板
        
        Args:
            fitness_level: 健身水平 ("beginner", "intermediate", "advanced")
            goal: 目标 ("lose_weight", "gain_muscle", "maintain")
            
        Returns:
            训练模板列表
        """
        if goal == "maintain":
            goal = "lose_weight"  # 维持体重使用减脂模板
        
        level = fitness_level.lower()
        if level not in self.templates:
            level = "beginner"
        
        if goal not in self.templates[level]:
            goal = "lose_weight"
        
        return self.templates[level][goal]
    
    def generate_plan(
        self,
        user_profile,
        days_per_week: int = 4
    ) -> Dict:
        """
        生成个性化训练计划
        
        Args:
            user_profile: 用户信息对象
            days_per_week: 每周训练天数
            
        Returns:
            个性化训练计划
        """
        fitness_level = user_profile.fitness_level.lower() if hasattr(user_profile, 'fitness_level') else "beginner"
        goal = user_profile.goal.lower() if hasattr(user_profile, 'goal') else "lose_weight"
        
        template = self.get_template(fitness_level, goal)
        
        # 根据训练天数选择模板
        selected_days = template[:min(days_per_week, len(template))]
        
        # 计算总消耗
        total_calories = sum(day.get("calories", 0) for day in selected_days)
        total_duration = sum(day.get("duration", 0) for day in selected_days)
        
        return {
            "fitness_level": fitness_level,
            "goal": goal,
            "days_per_week": days_per_week,
            "workouts": selected_days,
            "summary": {
                "total_weekly_duration": total_duration,
                "estimated_weekly_calories": total_calories,
                "rest_days": 7 - len(selected_days)
            },
            "tips": self._get_training_tips(fitness_level, goal)
        }
    
    def _get_training_tips(self, level: str, goal: str) -> List[str]:
        """获取训练提示"""
        tips = []
        
        if level == "beginner":
            tips.append("训练初期以掌握动作为主，不要追求重量")
            tips.append("每次训练前务必热身5-10分钟")
            tips.append("组间休息时可以进行轻度拉伸")
        
        if goal == "lose_weight":
            tips.append("有氧训练放在力量训练之后效果更佳")
            tips.append("高强度间歇训练(HIIT)燃脂效率更高")
            tips.append("训练后注意补充蛋白质帮助肌肉修复")
        elif goal == "gain_muscle":
            tips.append("力量训练优先保证动作标准和充足恢复")
            tips.append("每组训练后充分休息，不要急于完成")
            tips.append("保证每天每公斤体重摄入1.6-2g蛋白质")
        
        tips.append("保证7-8小时睡眠帮助恢复")
        tips.append("训练后补充水分和电解质")
        
        return tips
    
    def adjust_training(
        self,
        current_plan: List[Dict],
        feedback: Dict
    ) -> List[Dict]:
        """
        根据反馈调整训练计划
        
        Args:
            current_plan: 当前训练计划
            feedback: 用户反馈，包含:
                - fatigue_level: 疲劳程度 1-10
                - progress: 训练效果 ("good", "plateau", "hard")
                - injuries: 受伤部位列表
                - available_time: 可用时间(分钟)
                
        Returns:
            调整后的训练计划
        """
        adjusted_plan = []
        
        for day in current_plan:
            adjusted_day = day.copy()
            adjusted_exercises = []
            
            # 根据疲劳程度调整
            fatigue = feedback.get("fatigue_level", 5)
            
            if fatigue >= 8:  # 高疲劳
                # 减少训练量，降低强度
                for ex in day.get("exercises", []):
                    new_ex = ex.copy()
                    new_ex["sets"] = max(2, ex["sets"] - 1)
                    new_ex["rest"] = min(180, ex["rest"] + 30)
                    adjusted_exercises.append(new_ex)
                adjusted_day["intensity"] = "medium"
            elif fatigue <= 3:  # 低疲劳，感觉轻松
                # 增加训练量
                for ex in day.get("exercises", []):
                    new_ex = ex.copy()
                    new_ex["sets"] = min(6, ex["sets"] + 1)
                    adjusted_exercises.append(new_ex)
                adjusted_day["intensity"] = "high"
            else:
                adjusted_exercises = day.get("exercises", [])
            
            # 根据时间调整
            available_time = feedback.get("available_time", 60)
            if available_time < day.get("duration", 60):
                # 缩短训练
                for ex in adjusted_exercises[:3]:  # 只保留前3个动作
                    pass
                adjusted_day["duration"] = available_time
            
            adjusted_day["exercises"] = adjusted_exercises
            adjusted_plan.append(adjusted_day)
        
        return adjusted_plan
