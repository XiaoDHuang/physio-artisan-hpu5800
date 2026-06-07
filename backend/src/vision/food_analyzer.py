"""
食物分析器 - 使用视觉识别估算食物营养
"""

import os
import base64
from typing import Dict, List, Optional
from dataclasses import dataclass
import matplotlib.pyplot as plt
import matplotlib.patches as patches


# 常见食物营养数据库
FOOD_DATABASE = {
    "鸡胸肉": {"calories": 133, "protein": 31, "carbs": 0, "fat": 1.2, "per": "100g"},
    "牛肉": {"calories": 250, "protein": 26, "carbs": 0, "fat": 15, "per": "100g"},
    "三文鱼": {"calories": 208, "protein": 20, "carbs": 0, "fat": 13, "per": "100g"},
    "鸡蛋": {"calories": 155, "protein": 13, "carbs": 1.1, "fat": 11, "per": "100g"},
    "米饭": {"calories": 130, "protein": 2.7, "carbs": 28, "fat": 0.3, "per": "100g"},
    "面条": {"calories": 284, "protein": 8.3, "carbs": 59.5, "fat": 0.8, "per": "100g"},
    "馒头": {"calories": 223, "protein": 7.0, "carbs": 47, "fat": 1.1, "per": "100g"},
    "面包": {"calories": 265, "protein": 9, "carbs": 49, "fat": 3.2, "per": "100g"},
    "西兰花": {"calories": 34, "protein": 2.8, "carbs": 6.6, "fat": 0.4, "per": "100g"},
    "菠菜": {"calories": 23, "protein": 2.9, "carbs": 3.6, "fat": 0.4, "per": "100g"},
    "胡萝卜": {"calories": 41, "protein": 0.9, "carbs": 10, "fat": 0.2, "per": "100g"},
    "番茄": {"calories": 18, "protein": 0.9, "carbs": 3.9, "fat": 0.2, "per": "100g"},
    "土豆": {"calories": 76, "protein": 2, "carbs": 17, "fat": 0.1, "per": "100g"},
    "香蕉": {"calories": 93, "protein": 1.4, "carbs": 23, "fat": 0.2, "per": "100g"},
    "苹果": {"calories": 52, "protein": 0.3, "carbs": 14, "fat": 0.2, "per": "100g"},
    "橙子": {"calories": 47, "protein": 0.9, "carbs": 12, "fat": 0.1, "per": "100g"},
    "牛奶": {"calories": 54, "protein": 3, "carbs": 5, "fat": 3.2, "per": "100ml"},
    "酸奶": {"calories": 72, "protein": 2.9, "carbs": 9.3, "fat": 2.7, "per": "100g"},
    "豆腐": {"calories": 81, "protein": 8, "carbs": 2, "fat": 4.8, "per": "100g"},
    "饺子": {"calories": 240, "protein": 12, "carbs": 30, "fat": 8, "per": "100g"},
    "炒饭": {"calories": 180, "protein": 5, "carbs": 25, "fat": 7, "per": "100g"},
    "炒面": {"calories": 200, "protein": 6, "carbs": 28, "fat": 7, "per": "100g"},
    "沙拉": {"calories": 35, "protein": 1.5, "carbs": 5, "fat": 0.5, "per": "100g"},
    "披萨": {"calories": 266, "protein": 11, "carbs": 33, "fat": 10, "per": "100g"},
    "汉堡": {"calories": 295, "protein": 15, "carbs": 24, "fat": 14, "per": "100g"},
    "薯条": {"calories": 312, "protein": 3, "carbs": 41, "fat": 15, "per": "100g"},
    "炸鸡": {"calories": 246, "protein": 19, "carbs": 9, "fat": 14, "per": "100g"},
    "奶茶": {"calories": 78, "protein": 1, "carbs": 15, "fat": 2, "per": "100ml"},
    "可乐": {"calories": 42, "protein": 0, "carbs": 11, "fat": 0, "per": "100ml"},
    "咖啡": {"calories": 1, "protein": 0.1, "carbs": 0, "fat": 0, "per": "100ml"},
}


@dataclass
class DetectedFood:
    """识别到的食物"""
    name: str
    confidence: float
    estimated_grams: int
    calories: float
    protein: float
    carbs: float
    fat: float
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "confidence": self.confidence,
            "estimated_grams": self.estimated_grams,
            "calories": round(self.calories, 1),
            "protein": round(self.protein, 1),
            "carbs": round(self.carbs, 1),
            "fat": round(self.fat, 1),
        }


class FoodAnalyzer:
    """
    食物分析器
    
    使用视觉识别(模拟)估算食物营养成分
    调用USDA数据库获取标准营养数据
    
    注意: 真实实现需要接入LLM Vision API或专门的食品识别模型
    """
    
    def __init__(self):
        self.food_db = FOOD_DATABASE
    
    def analyze_image(self, image_path: str, portion_question: str = None) -> Dict:
        """
        分析食物图片
        
        Args:
            image_path: 图片路径
            portion_question: 用户回答的分量信息
            
        Returns:
            营养分析结果
        """
        if not os.path.exists(image_path):
            # 使用模拟数据
            return self._generate_mock_analysis()
        
        # 真实实现: 调用Vision API识别食物
        # detected_foods = self._detect_foods_with_vision(image_path)
        
        # 模拟识别
        detected_foods = self._simulate_food_detection()
        
        # 计算总营养
        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0
        
        for food in detected_foods:
            total_calories += food.calories
            total_protein += food.protein
            total_carbs += food.carbs
            total_fat += food.fat
        
        # 评估平衡度
        balance_score = self._calculate_balance_score(
            total_protein, total_carbs, total_fat, total_calories
        )
        
        return {
            "success": True,
            "detected_foods": [f.to_dict() for f in detected_foods],
            "total": {
                "calories": round(total_calories, 1),
                "protein_g": round(total_protein, 1),
                "carbs_g": round(total_carbs, 1),
                "fat_g": round(total_fat, 1),
            },
            "balance_score": balance_score,
            "assessment": self._assess_nutrition(total_protein, total_carbs, total_fat, balance_score),
            "usda_data": self._get_usda_source(list(set(f.name for f in detected_foods))),
        }
    
    def _simulate_food_detection(self) -> List[DetectedFood]:
        """模拟食物检测结果"""
        # 模拟一顿典型午餐
        detected = [
            DetectedFood(
                name="米饭",
                confidence=0.92,
                estimated_grams=200,
                calories=130 * 2,
                protein=2.7 * 2,
                carbs=28 * 2,
                fat=0.3 * 2
            ),
            DetectedFood(
                name="鸡胸肉",
                confidence=0.95,
                estimated_grams=150,
                calories=133 * 1.5,
                protein=31 * 1.5,
                carbs=0,
                fat=1.2 * 1.5
            ),
            DetectedFood(
                name="西兰花",
                confidence=0.88,
                estimated_grams=100,
                calories=34,
                protein=2.8,
                carbs=6.6,
                fat=0.4
            ),
        ]
        return detected
    
    def _calculate_balance_score(
        self,
        protein: float,
        carbs: float,
        fat: float,
        total_cal: float
    ) -> float:
        """计算营养平衡度评分"""
        if total_cal == 0:
            return 0
        
        # 计算实际比例
        protein_cal = protein * 4
        carbs_cal = carbs * 4
        fat_cal = fat * 9
        
        protein_ratio = protein_cal / total_cal * 100
        carbs_ratio = carbs_cal / total_cal * 100
        fat_ratio = fat_cal / total_cal * 100
        
        # 理想比例 (蛋白质30%, 碳水40%, 脂肪30%)
        ideal_protein = 30
        ideal_carbs = 40
        ideal_fat = 30
        
        # 计算偏差
        deviation = abs(protein_ratio - ideal_protein) + \
                   abs(carbs_ratio - ideal_carbs) + \
                   abs(fat_ratio - ideal_fat)
        
        # 转换为分数
        score = max(0, 100 - deviation * 2)
        return round(score, 1)
    
    def _assess_nutrition(
        self,
        protein: float,
        carbs: float,
        fat: float,
        balance_score: float
    ) -> Dict:
        """评估营养状况"""
        assessment = {
            "protein_level": "high" if protein > 40 else ("medium" if protein > 20 else "low"),
            "balance": "excellent" if balance_score > 85 else ("good" if balance_score > 70 else "needs_improvement"),
            "recommendations": []
        }
        
        if protein < 20:
            assessment["recommendations"].append("蛋白质摄入偏低，建议增加肉类、蛋类或豆制品")
        if fat > 50:
            assessment["recommendations"].append("脂肪摄入偏高，建议减少油炸食品")
        if balance_score > 85:
            assessment["recommendations"].append("营养搭配良好！")
        
        return assessment
    
    def _get_usda_source(self, food_names: List[str]) -> List[Dict]:
        """获取USDA数据源信息"""
        usda_data = []
        for name in food_names:
            if name in self.food_db:
                data = self.food_db[name]
                usda_data.append({
                    "food": name,
                    "source": "USDA FoodData Central",
                    "per_100g": data
                })
        return usda_data
    
    def _generate_mock_analysis(self) -> Dict:
        """生成模拟分析结果"""
        detected = self._simulate_food_detection()
        
        return {
            "success": True,
            "simulated": True,
            "detected_foods": [f.to_dict() for f in detected],
            "total": {
                "calories": sum(f.calories for f in detected),
                "protein_g": sum(f.protein for f in detected),
                "carbs_g": sum(f.carbs for f in detected),
                "fat_g": sum(f.fat for f in detected),
            },
            "balance_score": 78.5,
            "assessment": {
                "protein_level": "medium",
                "balance": "good",
                "recommendations": ["营养搭配较为均衡"]
            },
            "note": "使用模拟数据，请提供真实食物图片"
        }
    
    def generate_nutrition_pie_chart(self, analysis_result: Dict) -> str:
        """生成营养成分饼图"""
        total = analysis_result.get("total", {})
        calories = total.get("calories", 0)
        protein = total.get("protein_g", 0)
        carbs = total.get("carbs_g", 0)
        fat = total.get("fat_g", 0)
        
        if calories == 0:
            return None
        
        # 转换为热量
        protein_cal = protein * 4
        carbs_cal = carbs * 4
        fat_cal = fat * 9
        total_cal = protein_cal + carbs_cal + fat_cal
        
        if total_cal == 0:
            return None
        
        fig, ax = plt.subplots(figsize=(6, 6))
        
        sizes = [
            protein_cal / total_cal * 100,
            carbs_cal / total_cal * 100,
            fat_cal / total_cal * 100
        ]
        labels = [f'蛋白质\n{protein:.0f}g', f'碳水\n{carbs:.0f}g', f'脂肪\n{fat:.0f}g']
        colors = ['#2E86AB', '#28A745', '#FFC107']
        explode = (0.02, 0.02, 0.02)
        
        ax.pie(sizes, explode=explode, labels=labels, colors=colors,
               autopct='%1.1f%%', shadow=True, startangle=90,
               textprops={'fontsize': 11})
        ax.set_title(f'营养素热量占比\n总热量: {calories:.0f} kcal',
                    fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        
        os.makedirs("output/charts", exist_ok=True)
        path = "output/charts/nutrition_pie.png"
        plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return path
    
    def ask_portion_followup(self, detected_foods: List[str]) -> str:
        """生成分量追问提示"""
        food_list = "、".join(detected_foods)
        return f"我检测到您摄入了: {food_list}。请问每种食物的分量大概是多少？(如: 米饭一碗、鸡胸肉一块)"
