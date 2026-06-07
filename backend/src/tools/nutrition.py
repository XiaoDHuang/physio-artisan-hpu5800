"""
营养数据库
提供食物营养查询和饮食计划生成
"""

from typing import Dict, List, Optional


class NutritionDB:
    """营养数据库"""
    
    # 常见食物营养成分数据（每100g）
    FOOD_DATABASE = {
        # 主食类
        "米饭": {"calories": 116, "protein": 2.6, "carbs": 25.9, "fat": 0.3},
        "面条": {"calories": 284, "protein": 8.3, "carbs": 59.5, "fat": 0.8},
        "馒头": {"calories": 223, "protein": 7.0, "carbs": 47.0, "fat": 1.1},
        "全麦面包": {"calories": 247, "protein": 13, "carbs": 41, "fat": 3.4},
        
        # 蛋白质类
        "鸡胸肉": {"calories": 133, "protein": 31, "carbs": 0, "fat": 1.2},
        "牛肉": {"calories": 250, "protein": 26, "carbs": 0, "fat": 15},
        "三文鱼": {"calories": 208, "protein": 20, "carbs": 0, "fat": 13},
        "鸡蛋": {"calories": 155, "protein": 13, "carbs": 1.1, "fat": 11},
        "豆腐": {"calories": 81, "protein": 8, "carbs": 2, "fat": 4.8},
        
        # 蔬菜类
        "西兰花": {"calories": 34, "protein": 2.8, "carbs": 6.6, "fat": 0.4},
        "菠菜": {"calories": 23, "protein": 2.9, "carbs": 3.6, "fat": 0.4},
        "胡萝卜": {"calories": 41, "protein": 0.9, "carbs": 10, "fat": 0.2},
        "番茄": {"calories": 18, "protein": 0.9, "carbs": 3.9, "fat": 0.2},
        "黄瓜": {"calories": 15, "protein": 0.7, "carbs": 3.6, "fat": 0.1},
        
        # 水果类
        "香蕉": {"calories": 93, "protein": 1.4, "carbs": 23, "fat": 0.2},
        "苹果": {"calories": 52, "protein": 0.3, "carbs": 14, "fat": 0.2},
        "橙子": {"calories": 47, "protein": 0.9, "carbs": 12, "fat": 0.1},
        "蓝莓": {"calories": 57, "protein": 0.7, "carbs": 14, "fat": 0.3},
        
        # 奶制品
        "牛奶": {"calories": 54, "protein": 3, "carbs": 5, "fat": 3.2},
        "酸奶": {"calories": 72, "protein": 2.9, "carbs": 9.3, "fat": 2.7},
        "奶酪": {"calories": 402, "protein": 25, "carbs": 1.3, "fat": 33},
        
        # 坚果类
        "杏仁": {"calories": 579, "protein": 21, "carbs": 22, "fat": 50},
        "花生": {"calories": 567, "protein": 25, "carbs": 16, "fat": 49},
        
        # 饮品类
        "咖啡": {"calories": 1, "protein": 0.1, "carbs": 0, "fat": 0},
        "绿茶": {"calories": 1, "protein": 0, "carbs": 0.2, "fat": 0},
    }
    
    # 常见食物的份量估算（单位：克）
    PORTION_SIZES = {
        "米饭": 150,      # 一碗
        "面条": 200,      # 一碗
        "馒头": 100,      # 一个
        "全麦面包": 50,   # 一片
        "鸡胸肉": 150,    # 一块
        "牛肉": 150,      # 一块
        "三文鱼": 150,    # 一块
        "鸡蛋": 50,       # 一个
        "豆腐": 100,      # 一块
        "西兰花": 100,    # 一份
        "香蕉": 120,      # 一根
        "苹果": 200,      # 一个
        "牛奶": 250,      # 一杯
        "酸奶": 150,      # 一杯
    }
    
    def __init__(self):
        self.db = self.FOOD_DATABASE
    
    def search(self, food_name: str) -> Optional[Dict]:
        """
        搜索食物营养信息
        
        Args:
            food_name: 食物名称
            
        Returns:
            营养信息字典，包含热量、蛋白质、碳水、脂肪（每100g）
        """
        # 精确匹配
        if food_name in self.db:
            return self.db[food_name].copy()
        
        # 模糊匹配
        food_name_lower = food_name.lower()
        for name, nutrition in self.db.items():
            if food_name_lower in name.lower() or name.lower() in food_name_lower:
                result = nutrition.copy()
                result["name"] = name
                result["portion_g"] = self.PORTION_SIZES.get(name, 100)
                return result
        
        return None
    
    def calculate_meal_nutrition(self, foods: List[Dict]) -> Dict:
        """
        计算一餐的营养总量
        
        Args:
            foods: 食物列表，每项包含name和portion_g
                   例如: [{"name": "鸡胸肉", "portion_g": 150}, ...]
                   
        Returns:
            总营养信息
        """
        total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
        
        for food in foods:
            name = food.get("name")
            portion = food.get("portion_g", self.PORTION_SIZES.get(name, 100))
            
            nutrition = self.search(name)
            if nutrition:
                factor = portion / 100
                total["calories"] += nutrition["calories"] * factor
                total["protein"] += nutrition["protein"] * factor
                total["carbs"] += nutrition["carbs"] * factor
                total["fat"] += nutrition["fat"] * factor
        
        # 四舍五入
        return {k: round(v, 1) for k, v in total.items()}
    
    def get_meal_plan(
        self,
        target_calories: int,
        macro_ratio: str = "40/30/30",
        meals_per_day: int = 3
    ) -> Dict:
        """
        生成饮食计划
        
        Args:
            target_calories: 目标卡路里
            macro_ratio: 宏量营养素比例 "蛋白质/碳水/脂肪"
            meals_per_day: 每日餐数
            
        Returns:
            饮食计划，包含各餐建议
        """
        # 解析宏量比例
        ratios = [int(x) / 100 for x in macro_ratio.split("/")]
        protein_ratio, carb_ratio, fat_ratio = ratios
        
        # 计算各餐热量分配
        meal_calories = target_calories / meals_per_day
        
        # 生成各餐建议
        meal_suggestions = {
            1: {  # 早餐
                "name": "早餐",
                "calories": int(meal_calories * 1.2),  # 早餐稍高
                "suggestions": [
                    {"name": "鸡蛋", "portion_g": 100, "reason": "优质蛋白"},
                    {"name": "全麦面包", "portion_g": 50, "reason": "复合碳水"},
                    {"name": "牛奶", "portion_g": 250, "reason": "钙和蛋白"}
                ]
            },
            2: {  # 午餐
                "name": "午餐",
                "calories": int(meal_calories * 1.4),  # 午餐最高
                "suggestions": [
                    {"name": "鸡胸肉", "portion_g": 150, "reason": "低脂蛋白"},
                    {"name": "米饭", "portion_g": 150, "reason": "能量来源"},
                    {"name": "西兰花", "portion_g": 100, "reason": "膳食纤维"}
                ]
            },
            3: {  # 晚餐
                "name": "晚餐",
                "calories": int(meal_calories * 0.9),  # 晚餐略低
                "suggestions": [
                    {"name": "牛肉", "portion_g": 120, "reason": "蛋白质"},
                    {"name": "蔬菜", "portion_g": 200, "reason": "饱腹感"}
                ]
            }
        }
        
        # 计算总营养
        total_nutrition = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
        for meal_key, meal in meal_suggestions.items():
            meal_nutrition = self.calculate_meal_nutrition(meal["suggestions"])
            for k, v in meal_nutrition.items():
                total_nutrition[k] += v
        
        return {
            "target_calories": target_calories,
            "macro_ratio": macro_ratio,
            "meals": meal_suggestions,
            "total_nutrition": {k: round(v, 1) for k, v in total_nutrition.items()},
            "protein_target": round(target_calories * protein_ratio / 4),
            "carbs_target": round(target_calories * carb_ratio / 4),
            "fat_target": round(target_calories * fat_ratio / 9)
        }
    
    def suggest_snacks(
        self,
        remaining_calories: int,
        preferred_type: str = "any"
    ) -> List[Dict]:
        """
        根据剩余热量推荐健康零食
        
        Args:
            remaining_calories: 剩余可摄入热量
            preferred_type: 偏好类型 ("protein", "fruit", "nut", "any")
        """
        suggestions = []
        
        for name, nutrition in self.db.items():
            if nutrition["calories"] <= remaining_calories:
                # 根据类型筛选
                if preferred_type == "protein" and name in ["鸡蛋", "豆腐", "鸡胸肉"]:
                    suggestions.append({
                        "name": name,
                        "portion": self.PORTION_SIZES.get(name, 100),
                        "calories": nutrition["calories"]
                    })
                elif preferred_type == "fruit" and name in ["香蕉", "苹果", "橙子", "蓝莓"]:
                    suggestions.append({
                        "name": name,
                        "portion": self.PORTION_SIZES.get(name, 100),
                        "calories": nutrition["calories"]
                    })
                elif preferred_type == "nut" and name in ["杏仁", "花生"]:
                    suggestions.append({
                        "name": name,
                        "portion": self.PORTION_SIZES.get(name, 100),
                        "calories": nutrition["calories"]
                    })
                elif preferred_type == "any":
                    suggestions.append({
                        "name": name,
                        "portion": self.PORTION_SIZES.get(name, 100),
                        "calories": nutrition["calories"]
                    })
        
        return sorted(suggestions, key=lambda x: x["calories"], reverse=True)[:5]
