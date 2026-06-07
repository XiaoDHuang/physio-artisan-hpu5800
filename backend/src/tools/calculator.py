"""
身体指标计算器
提供BMI、BMR、TDEE、身体年龄等计算功能
"""

from typing import Dict, Optional


class BodyMetricsCalculator:
    """身体指标计算器"""
    
    # 活动水平系数
    ACTIVITY_MULTIPLIERS = {
        "sedentary": 1.2,      # 久坐，少量运动
        "light": 1.375,        # 轻度活跃，每周1-3天运动
        "moderate": 1.55,      # 中度活跃，每周3-5天运动
        "active": 1.725,       # 非常活跃，每周6-7天运动
        "very_active": 1.9     # 极度活跃，运动员/体力劳动者
    }
    
    def __init__(self, user_profile=None):
        self.user_profile = user_profile
    
    def calculate_bmi(self, weight_kg: float, height_cm: float) -> float:
        """
        计算BMI (Body Mass Index)
        BMI = 体重(kg) / 身高(m)^2
        
        返回: BMI值
        - < 18.5: 偏瘦
        - 18.5-24: 正常
        - 24-28: 超重
        - > 28: 肥胖
        """
        height_m = height_cm / 100
        return weight_kg / (height_m ** 2)
    
    def get_bmi_category(self, bmi: float) -> Dict[str, str]:
        """获取BMI分类"""
        if bmi < 18.5:
            category = "偏瘦"
            color = "blue"
        elif bmi < 24:
            category = "正常"
            color = "green"
        elif bmi < 28:
            category = "超重"
            color = "yellow"
        else:
            category = "肥胖"
            color = "red"
        
        return {
            "category": category,
            "color": color,
            "ideal_weight_min": 18.5 * (self.user_profile.height_cm / 100) ** 2 if self.user_profile else 0,
            "ideal_weight_max": 24 * (self.user_profile.height_cm / 100) ** 2 if self.user_profile else 0
        }
    
    def calculate_bmr(
        self,
        weight_kg: float,
        height_cm: float,
        age: int,
        gender: str
    ) -> float:
        """
        计算基础代谢率 (Basal Metabolic Rate)
        使用Mifflin-St Jeor公式
        
        男性: BMR = 10*体重 + 6.25*身高 - 5*年龄 + 5
        女性: BMR = 10*体重 + 6.25*身高 - 5*年龄 - 161
        """
        if gender.lower() in ["male", "男", "男性"]:
            bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
        else:
            bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
        
        return bmr
    
    def calculate_tdee(
        self,
        bmr: float,
        activity_level: str
    ) -> float:
        """
        计算每日总能量消耗 (Total Daily Energy Expenditure)
        TDEE = BMR * 活动系数
        """
        multiplier = self.ACTIVITY_MULTIPLIERS.get(
            activity_level.lower(),
            1.55  # 默认中等活跃
        )
        return bmr * multiplier
    
    def calculate_macro_needs(
        self,
        tdee: float,
        goal: str,
        protein_ratio: float = 0.30,
        carb_ratio: float = 0.40,
        fat_ratio: float = 0.30
    ) -> Dict[str, float]:
        """
        计算宏量营养素需求
        
        目标:
        - lose_weight: 保持TDEE或略低
        - maintain: 维持TDEE
        - gain_muscle: TDEE * 1.1
        
        返回: 蛋白质、碳水、脂肪的克数
        """
        if goal == "lose_weight":
            target_cal = tdee * 0.8
        elif goal == "gain_muscle":
            target_cal = tdee * 1.1
        else:
            target_cal = tdee
        
        protein_cal = target_cal * protein_ratio
        carb_cal = target_cal * carb_ratio
        fat_cal = target_cal * fat_ratio
        
        return {
            "target_calories": round(target_cal),
            "protein_g": round(protein_cal / 4),    # 蛋白质4kcal/g
            "carbs_g": round(carb_cal / 4),          # 碳水4kcal/g
            "fat_g": round(fat_cal / 9),             # 脂肪9kcal/g
            "macro_ratio": f"{int(protein_ratio*100)}/{int(carb_ratio*100)}/{int(fat_ratio*100)}"
        }
    
    def calculate_body_age(
        self,
        resting_heart_rate: int,
        bmi: float,
        exercise_frequency: int,  # 每周运动次数
        sleep_quality: float      # 1-10
    ) -> int:
        """
        估算身体年龄
        这是一个综合指标，基于:
        - 静息心率（越低越好）
        - BMI（正常范围最佳）
        - 运动频率
        - 睡眠质量
        
        注意：这是一个粗略估算，不作为医疗依据
        """
        base_age = 30  # 基准年龄
        
        # 心率评分 (正常静息心率60-100)
        if resting_heart_rate < 60:
            hr_score = -5  # 运动员水平
        elif resting_heart_rate < 70:
            hr_score = -3
        elif resting_heart_rate < 80:
            hr_score = 0
        elif resting_heart_rate < 90:
            hr_score = 3
        else:
            hr_score = 5
        
        # BMI评分
        if 18.5 <= bmi < 24:
            bmi_score = 0
        elif 24 <= bmi < 28:
            bmi_score = 3
        elif bmi >= 28:
            bmi_score = 6
        else:  # < 18.5
            bmi_score = 2
        
        # 运动频率评分
        if exercise_frequency >= 5:
            exercise_score = -5
        elif exercise_frequency >= 3:
            exercise_score = -3
        elif exercise_frequency >= 1:
            exercise_score = 0
        else:
            exercise_score = 3
        
        # 睡眠评分
        if sleep_quality >= 8:
            sleep_score = -2
        elif sleep_quality >= 6:
            sleep_score = 0
        else:
            sleep_score = 3
        
        # 计算估算年龄
        estimated_age = base_age + hr_score + bmi_score + exercise_score + sleep_score
        
        # 确保年龄在合理范围内
        return max(18, min(80, estimated_age))
    
    def calculate_calorie_burn(
        self,
        exercise_type: str,
        duration_minutes: int,
        weight_kg: float
    ) -> int:
        """
        计算运动消耗卡路里
        
        常见运动每小时消耗估算（kcal/kg体重）:
        - 步行: 3.5
        - 慢跑: 7.0
        - 快跑: 10.0
        - 骑行: 5.5
        - 游泳: 8.0
        - 力量训练: 6.0
        - HIIT: 12.0
        """
        burn_rates = {
            "walking": 3.5,
            "jogging": 7.0,
            "running": 10.0,
            "cycling": 5.5,
            "swimming": 8.0,
            "strength": 6.0,
            "hiit": 12.0,
            "yoga": 3.0,
            "basketball": 8.0,
            "soccer": 9.0
        }
        
        rate = burn_rates.get(exercise_type.lower(), 5.0)
        calories_per_min = rate * weight_kg / 60
        
        return int(calories_per_min * duration_minutes)
    
    def calculate_water_intake(
        self,
        weight_kg: float,
        exercise_minutes: int = 0
    ) -> int:
        """
        计算每日建议饮水量
        基础: 30-35ml/kg
        运动: 每30分钟额外增加500ml
        """
        base_ml = weight_kg * 35
        exercise_ml = (exercise_minutes / 30) * 500
        
        return int(base_ml + exercise_ml)
