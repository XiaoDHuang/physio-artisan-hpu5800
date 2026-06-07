"""
数据上传处理器
处理手表数据、视频、食物图片的上传
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import base64


# 上传目录配置
UPLOAD_DIR = "uploads"
DATA_DIR = os.path.join(UPLOAD_DIR, "data")
WATCH_DIR = os.path.join(UPLOAD_DIR, "watch_data")
VIDEO_DIR = os.path.join(UPLOAD_DIR, "videos")
IMAGE_DIR = os.path.join(UPLOAD_DIR, "images")

# 确保目录存在
for d in [UPLOAD_DIR, DATA_DIR, WATCH_DIR, VIDEO_DIR, IMAGE_DIR]:
    os.makedirs(d, exist_ok=True)


@dataclass
class UploadResult:
    """上传结果"""
    success: bool
    file_path: str
    file_type: str
    file_size: int
    error: Optional[str] = None
    parsed_data: Optional[Dict] = None


class DataUploader:
    """
    数据上传处理器
    
    支持:
    - 华为手表JSON数据
    - 运动视频
    - 食物图片
    """
    
    def __init__(self):
        self.watch_parser = WatchDataParser()
        self.video_validator = VideoValidator()
        self.image_validator = ImageValidator()
    
    def upload_watch_data(self, file) -> UploadResult:
        """
        上传手表数据
        
        支持格式:
        - 华为运动健康App导出的JSON
        - Apple Health导出的XML/JSON
        - 通用JSON格式
        """
        try:
            # 读取文件内容
            content = file.read()
            
            # 尝试解析JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                return UploadResult(
                    success=False,
                    file_path="",
                    file_type="json",
                    file_size=len(content),
                    error="无效的JSON格式"
                )
            
            # 保存文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"watch_{timestamp}.json"
            filepath = os.path.join(WATCH_DIR, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 解析数据
            parsed = self.watch_parser.parse(data)
            
            return UploadResult(
                success=True,
                file_path=filepath,
                file_type="json",
                file_size=len(content),
                parsed_data=parsed
            )
            
        except Exception as e:
            return UploadResult(
                success=False,
                file_path="",
                file_type="json",
                file_size=0,
                error=str(e)
            )
    
    def upload_video(self, file, user_id: str = "default") -> UploadResult:
        """
        上传运动视频
        
        支持格式: mp4, avi, mov
        """
        # 验证格式
        if not self.video_validator.validate(file.name):
            return UploadResult(
                success=False,
                file_path="",
                file_type="video",
                file_size=0,
                error="不支持的视频格式"
            )
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = os.path.splitext(file.name)[1]
            filename = f"exercise_{user_id}_{timestamp}{ext}"
            filepath = os.path.join(VIDEO_DIR, filename)
            
            # 保存文件
            with open(filepath, 'wb') as f:
                f.write(file.read())
            
            return UploadResult(
                success=True,
                file_path=filepath,
                file_type="video",
                file_size=os.path.getsize(filepath)
            )
            
        except Exception as e:
            return UploadResult(
                success=False,
                file_path="",
                file_type="video",
                file_size=0,
                error=str(e)
            )
    
    def upload_food_image(self, file, user_id: str = "default") -> UploadResult:
        """上传食物图片"""
        # 验证格式
        if not self.image_validator.validate(file.name):
            return UploadResult(
                success=False,
                file_path="",
                file_type="image",
                file_size=0,
                error="不支持的图片格式"
            )
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = os.path.splitext(file.name)[1]
            filename = f"food_{user_id}_{timestamp}{ext}"
            filepath = os.path.join(IMAGE_DIR, filename)
            
            # 保存文件
            with open(filepath, 'wb') as f:
                f.write(file.read())
            
            return UploadResult(
                success=True,
                file_path=filepath,
                file_type="image",
                file_size=os.path.getsize(filepath)
            )
            
        except Exception as e:
            return UploadResult(
                success=False,
                file_path="",
                file_type="image",
                file_size=0,
                error=str(e)
            )


class WatchDataParser:
    """
    手表数据解析器
    
    支持多种数据格式:
    - 华为运动健康
    - Apple Health
    - Fitbit
    - 通用JSON
    """
    
    # 华为手表数据字段映射
    HUAWEI_MAPPING = {
        "steps": ["steps", "步数", "stepCount"],
        "exercise_minutes": ["exerciseMinutes", "运动时长", "activeMinutes"],
        "calories_burned": ["calories", "卡路里", "caloriesBurned", "energyExpenditure"],
        "heart_rate_avg": ["heartRateAvg", "心率平均值", "heartRate"],
        "heart_rate_rest": ["heartRateRest", "静息心率", "restingHeartRate"],
        "sleep_total": ["sleepDuration", "睡眠时长", "totalSleepDuration"],
        "sleep_deep": ["deepSleepDuration", "深睡时长", "deepSleep"],
    }
    
    def parse(self, data: Dict) -> Dict:
        """
        解析手表数据
        
        自动检测数据格式并解析
        """
        # 检测数据源
        source = self._detect_source(data)
        
        if source == "huawei":
            return self._parse_huawei(data)
        elif source == "apple":
            return self._parse_apple(data)
        elif source == "generic":
            return self._parse_generic(data)
        else:
            return self._parse_generic(data)
    
    def _detect_source(self, data: Dict) -> str:
        """检测数据来源"""
        # 华为特征字段
        huawei_keys = ["stepCount", "calories", "heartRate", "sleepDuration"]
        if any(k in data for k in huawei_keys):
            return "huawei"
        
        # Apple Health特征
        apple_keys = ["ActivitySummaries", "HealthData"]
        if any(k in data for k in apple_keys):
            return "apple"
        
        return "generic"
    
    def _parse_huawei(self, data: Dict) -> Dict:
        """解析华为数据"""
        parsed = {}
        
        for target, sources in self.HUAWEI_MAPPING.items():
            for source in sources:
                if source in data:
                    parsed[target] = data[source]
                    break
        
        # 解析HRV数据
        if "hrv" in data or "HRV" in data:
            parsed["hrv_data"] = data.get("hrv", data.get("HRV", {}))
        
        # 解析睡眠详情
        if "sleep" in data or "sleepData" in data:
            sleep = data.get("sleep", data.get("sleepData", {}))
            parsed["sleep_data"] = {
                "total_hours": sleep.get("duration", sleep.get("totalHours", 0)) / 3600 if isinstance(sleep.get("duration", 0), int) else sleep.get("totalHours", 7),
                "deep_sleep_percent": sleep.get("deepSleepPercent", 20),
                "rem_sleep_percent": sleep.get("remSleepPercent", 22),
                "sleep_score": sleep.get("score", 80)
            }
        
        return parsed
    
    def _parse_apple(self, data: Dict) -> Dict:
        """解析Apple Health数据"""
        parsed = {}
        
        # 解析活动摘要
        if "ActivitySummaries" in data:
            summaries = data["ActivitySummaries"]
            if summaries:
                summary = summaries[-1]  # 取最新的
                parsed["steps"] = summary.get("activeEnergyBurned", 0)
                parsed["calories_burned"] = summary.get("activeEnergyBurned", 0)
        
        return parsed
    
    def _parse_generic(self, data: Dict) -> Dict:
        """解析通用格式"""
        parsed = {}
        
        # 通用字段匹配
        field_mapping = {
            "steps": ["steps", "步数", "step"],
            "calories": ["calories", "卡路里", "cal"],
            "heart_rate": ["heart_rate", "心率", "hr"],
            "sleep": ["sleep", "睡眠"]
        }
        
        for target, sources in field_mapping.items():
            for source in sources:
                if source in data:
                    parsed[target] = data[source]
                    break
        
        return parsed


class VideoValidator:
    """视频验证器"""
    ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv'}
    MAX_SIZE_MB = 100
    
    def validate(self, filename: str) -> bool:
        """验证视频文件"""
        ext = os.path.splitext(filename.lower())[1]
        return ext in self.ALLOWED_EXTENSIONS


class ImageValidator:
    """图片验证器"""
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
    MAX_SIZE_MB = 10
    
    def validate(self, filename: str) -> bool:
        """验证图片文件"""
        ext = os.path.splitext(filename.lower())[1]
        return ext in self.ALLOWED_EXTENSIONS


# 示例数据生成器（用于演示）
def generate_sample_watch_data() -> Dict:
    """生成示例手表数据"""
    import random
    from datetime import datetime, timedelta
    
    base_date = datetime.now() - timedelta(days=1)
    
    return {
        "date": base_date.strftime("%Y-%m-%d"),
        "steps": random.randint(8000, 15000),
        "exercise_minutes": random.randint(30, 90),
        "calories_burned": random.randint(2000, 3200),
        "heart_rate_avg": random.randint(65, 85),
        "heart_rate_rest": random.randint(52, 65),
        "heart_rate_max": random.randint(150, 180),
        "hrv_data": {
            "sdnn": random.randint(35, 55),
            "rmssd": random.randint(28, 48),
            "lf_hf_ratio": round(random.uniform(0.8, 1.5), 2)
        },
        "sleep_data": {
            "total_hours": round(random.uniform(6.5, 8.5), 1),
            "deep_sleep_percent": random.randint(15, 25),
            "rem_sleep_percent": random.randint(20, 28),
            "light_sleep_percent": random.randint(50, 60),
            "sleep_score": random.randint(70, 90)
        },
        "stress_level": random.randint(30, 60),
        "blood_oxygen": random.randint(95, 99),
        "temperature": round(random.uniform(36.2, 36.8), 1)
    }


def generate_sample_food_data() -> Dict:
    """生成示例食物数据"""
    return {
        "meal_type": "lunch",
        "foods": [
            {"name": "米饭", "grams": 200, "calories": 260},
            {"name": "鸡胸肉", "grams": 150, "calories": 200},
            {"name": "西兰花", "grams": 100, "calories": 34},
            {"name": "番茄炒蛋", "grams": 150, "calories": 150}
        ],
        "total_calories": 644,
        "total_protein": 55,
        "total_carbs": 85,
        "total_fat": 12
    }
