"""
模拟运动手表数据生成器
用于演示和测试
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json


class WatchDataSimulator:
    """
    模拟运动手表数据生成器
    
    支持生成：
    - 运动数据（步数、心率、卡路里）
    - 睡眠数据（时长、深睡比例）
    - 饮食数据（热量、营养素）
    """
    
    def __init__(self, seed: int = None):
        if seed:
            random.seed(seed)
        self.base_profile = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 28,
            "gender": "male",
            "fitness_level": "intermediate",
            "goal": "lose_weight"
        }
    
    def generate_daily_data(
        self,
        date: str = None,
        day_type: str = "workday"  # "workday", "weekend", "rest_day", "training_day"
    ) -> Dict:
        """
        生成单日健康数据
        
        Args:
            date: 日期字符串，格式YYYY-MM-DD
            day_type: 日期类型
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # 根据日期类型设置不同的基准
        if day_type == "training_day":
            steps, exercise_min, calories_burned = self._training_day_stats()
            sleep_hours, deep_sleep_pct = 7.5, 22
        elif day_type == "weekend":
            steps, exercise_min, calories_burned = self._weekend_stats()
            sleep_hours, deep_sleep_pct = 8.0, 20
        elif day_type == "rest_day":
            steps, exercise_min, calories_burned = self._rest_day_stats()
            sleep_hours, deep_sleep_pct = 7.5, 18
        else:  # workday
            steps, exercise_min, calories_burned = self._workday_stats()
            sleep_hours, deep_sleep_pct = 6.5, 17
        
        # 添加随机波动
        steps = int(steps * random.uniform(0.85, 1.15))
        exercise_min = int(exercise_min * random.uniform(0.8, 1.2))
        calories_burned = int(calories_burned * random.uniform(0.9, 1.1))
        
        # 饮食数据
        calorie_intake = self._generate_calorie_intake(day_type)
        
        # 计算心率（基于运动强度）
        if day_type == "training_day":
            heart_rate_avg = random.randint(130, 150)
        elif exercise_min > 30:
            heart_rate_avg = random.randint(110, 130)
        else:
            heart_rate_avg = random.randint(70, 85)
        
        return {
            "date": date,
            "steps": steps,
            "exercise_minutes": exercise_min,
            "calories_burned": calories_burned,
            "heart_rate_avg": heart_rate_avg,
            "calories_intake": calorie_intake,
            "protein_g": int(calorie_intake * 0.18 / 4),  # 18%蛋白
            "carbs_g": int(calorie_intake * 0.45 / 4),    # 45%碳水
            "fat_g": int(calorie_intake * 0.32 / 9),      # 32%脂肪
            "sleep_hours": round(sleep_hours * random.uniform(0.95, 1.05), 1),
            "deep_sleep_percent": round(deep_sleep_pct * random.uniform(0.9, 1.1), 1),
            "sleep_quality": self._calculate_sleep_quality(sleep_hours, deep_sleep_pct),
            "day_type": day_type
        }
    
    def _workday_stats(self) -> tuple:
        """工作日数据"""
        steps = random.randint(6000, 10000)
        exercise_min = random.randint(20, 45)
        calories_burned = random.randint(1800, 2200)
        return steps, exercise_min, calories_burned
    
    def _weekend_stats(self) -> tuple:
        """周末数据"""
        steps = random.randint(8000, 15000)
        exercise_min = random.randint(30, 90)
        calories_burned = random.randint(2000, 2800)
        return steps, exercise_min, calories_burned
    
    def _rest_day_stats(self) -> tuple:
        """休息日数据"""
        steps = random.randint(3000, 6000)
        exercise_min = random.randint(0, 20)
        calories_burned = random.randint(1600, 1900)
        return steps, exercise_min, calories_burned
    
    def _training_day_stats(self) -> tuple:
        """训练日数据"""
        steps = random.randint(10000, 18000)
        exercise_min = random.randint(60, 90)
        calories_burned = random.randint(2500, 3500)
        return steps, exercise_min, calories_burned
    
    def _generate_calorie_intake(self, day_type: str) -> int:
        """生成摄入热量"""
        if day_type == "training_day":
            return random.randint(2200, 2600)
        elif day_type == "weekend":
            return random.randint(2000, 2400)
        elif day_type == "rest_day":
            return random.randint(1600, 1900)
        else:
            return random.randint(1800, 2100)
    
    def _calculate_sleep_quality(self, hours: float, deep_pct: float) -> int:
        """计算睡眠质量评分"""
        score = 5  # 基础分
        
        # 时长评分
        if 7 <= hours <= 9:
            score += 2
        elif 6 <= hours < 7 or 9 < hours <= 10:
            score += 1
        elif hours < 5 or hours > 10:
            score -= 1
        
        # 深睡比例评分
        if 15 <= deep_pct <= 25:
            score += 2
        elif 10 <= deep_pct < 15 or 25 < deep_pct <= 30:
            score += 1
        elif deep_pct < 10:
            score -= 1
        
        return max(1, min(10, score))
    
    def generate_weekly_data(self, start_date: str = None) -> List[Dict]:
        """生成一周数据"""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=6)
        elif isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        
        week_data = []
        day_types = ["workday", "workday", "workday", "training_day", 
                     "workday", "weekend", "weekend"]
        
        for i in range(7):
            date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            day_type = day_types[i]
            data = self.generate_daily_data(date, day_type)
            week_data.append(data)
        
        return week_data
    
    def generate_monthly_data(self, year: int = None, month: int = None) -> List[Dict]:
        """生成一个月数据"""
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month
        
        from calendar import monthrange
        days_in_month = monthrange(year, month)[1]
        
        month_data = []
        for day in range(1, days_in_month + 1):
            date = f"{year:04d}-{month:02d}-{day:02d}"
            
            # 周末类型判断
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            weekday = date_obj.weekday()
            
            if weekday >= 5:  # 周末
                day_type = "weekend" if random.random() > 0.3 else "training_day"
            else:
                if random.random() < 0.3:
                    day_type = "training_day"
                elif random.random() < 0.2:
                    day_type = "rest_day"
                else:
                    day_type = "workday"
            
            data = self.generate_daily_data(date, day_type)
            month_data.append(data)
        
        return month_data
    
    def generate_sample_health_data(self) -> Dict:
        """生成示例健康数据（用于演示）"""
        return {
            "user_profile": {
                "name": "张三",
                "age": 28,
                "gender": "男",
                "height_cm": 175,
                "weight_kg": 72,
                "fitness_level": "中级",
                "goal": "减脂",
                "activity_level": "活跃"
            },
            "today_data": self.generate_daily_data(
                datetime.now().strftime("%Y-%m-%d"),
                "training_day"
            ),
            "weekly_summary": self._generate_weekly_summary(),
            "goals": {
                "daily_steps": 10000,
                "daily_exercise_min": 60,
                "daily_calorie_burn": 2500,
                "daily_sleep_hours": 8,
                "daily_protein_g": 120,
                "daily_calorie_limit": 2000
            }
        }
    
    def _generate_weekly_summary(self) -> Dict:
        """生成周汇总数据"""
        week_data = self.generate_weekly_data()
        
        return {
            "avg_steps": int(sum(d["steps"] for d in week_data) / 7),
            "avg_exercise_min": int(sum(d["exercise_minutes"] for d in week_data) / 7),
            "avg_calories_burned": int(sum(d["calories_burned"] for d in week_data) / 7),
            "avg_calories_intake": int(sum(d["calories_intake"] for d in week_data) / 7),
            "avg_sleep_hours": round(sum(d["sleep_hours"] for d in week_data) / 7, 1),
            "total_workouts": sum(1 for d in week_data if d["day_type"] == "training_day"),
            "best_day": max(week_data, key=lambda x: x["steps"])["date"],
            "trend": "improving"  # or "stable", "declining"
        }
    
    def export_to_json(self, data: List[Dict], filepath: str):
        """导出数据到JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def export_to_csv(self, data: List[Dict], filepath: str):
        """导出数据到CSV文件"""
        if not data:
            return
        
        import csv
        
        keys = data[0].keys()
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)


# 使用示例
if __name__ == "__main__":
    simulator = WatchDataSimulator(seed=42)
    
    # 生成今日数据
    today_data = simulator.generate_daily_data(
        datetime.now().strftime("%Y-%m-%d"),
        "training_day"
    )
    print("今日健康数据:")
    print(json.dumps(today_data, ensure_ascii=False, indent=2))
    
    # 生成一周数据
    week_data = simulator.generate_weekly_data()
    print(f"\n本周数据共 {len(week_data)} 天")
    
    # 生成示例数据
    sample = simulator.generate_sample_health_data()
    print("\n示例健康数据:")
    print(json.dumps(sample, ensure_ascii=False, indent=2))
