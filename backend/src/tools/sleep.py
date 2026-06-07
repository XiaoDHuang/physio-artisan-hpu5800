"""
睡眠分析器
分析睡眠数据并提供建议
"""

from typing import Dict, List, Optional


class SleepAnalyzer:
    """睡眠分析器"""
    
    # 睡眠阶段参考值
    SLEEP_STAGES = {
        "deep_sleep": {
            "optimal_min": 15,  # 深睡眠应占15-25%
            "optimal_max": 25,
            "description": "深睡眠是恢复性睡眠，对身体修复至关重要"
        },
        "light_sleep": {
            "optimal_min": 45,
            "optimal_max": 55,
            "description": "浅睡眠帮助记忆整合"
        },
        "rem": {
            "optimal_min": 20,
            "optimal_max": 25,
            "description": "REM睡眠与学习、情绪调节相关"
        }
    }
    
    # 睡眠质量评分标准
    QUALITY_SCALE = {
        "excellent": {"min": 9, "max": 10, "color": "green"},
        "good": {"min": 7, "max": 8, "color": "light_green"},
        "fair": {"min": 5, "max": 6, "color": "yellow"},
        "poor": {"min": 3, "max": 4, "color": "orange"},
        "very_poor": {"min": 1, "max": 2, "color": "red"}
    }
    
    def __init__(self):
        self.stages = self.SLEEP_STAGES
        self.quality_scale = self.QUALITY_SCALE
    
    def analyze(
        self,
        sleep_hours: float,
        deep_sleep_percent: float,
        quality_score: int
    ) -> Dict:
        """
        分析睡眠质量
        
        Args:
            sleep_hours: 睡眠时长（小时）
            deep_sleep_percent: 深睡眠比例（%）
            quality_score: 质量评分（1-10）
            
        Returns:
            睡眠分析结果
        """
        # 计算睡眠阶段
        light_sleep_percent = 100 - deep_sleep_percent - 22  # 假设REM占22%
        
        # 评估睡眠时长
        duration_assessment = self._assess_duration(sleep_hours)
        
        # 评估深睡眠
        deep_sleep_assessment = self._assess_deep_sleep(deep_sleep_percent)
        
        # 综合评分
        overall_score = self._calculate_overall_score(
            sleep_hours, deep_sleep_percent, quality_score
        )
        
        # 获取建议
        recommendations = self._generate_recommendations(
            sleep_hours, deep_sleep_percent, quality_score
        )
        
        return {
            "sleep_hours": sleep_hours,
            "deep_sleep_percent": deep_sleep_percent,
            "light_sleep_percent": max(0, light_sleep_percent),
            "rem_sleep_percent": 22,  # 估算值
            "quality_score": quality_score,
            "overall_score": overall_score,
            "duration_assessment": duration_assessment,
            "deep_sleep_assessment": deep_sleep_assessment,
            "recommendations": recommendations,
            "sleep_stage_chart": self._generate_stage_chart(
                sleep_hours, deep_sleep_percent, light_sleep_percent
            )
        }
    
    def _assess_duration(self, hours: float) -> Dict:
        """评估睡眠时长"""
        optimal_min, optimal_max = 7.0, 9.0
        
        if hours < 5:
            status = "严重不足"
            color = "red"
            deficit = optimal_min - hours
        elif hours < 6:
            status = "不足"
            color = "orange"
            deficit = optimal_min - hours
        elif hours < 7:
            status = "略少"
            color = "yellow"
            deficit = optimal_min - hours
        elif hours <= 9:
            status = "充足"
            color = "green"
            deficit = 0
        else:
            status = "过多"
            color = "yellow"
            deficit = 0
        
        return {
            "status": status,
            "color": color,
            "deficit_hours": round(max(0, deficit), 1),
            "optimal_range": f"{optimal_min}-{optimal_max}小时"
        }
    
    def _assess_deep_sleep(self, deep_percent: float) -> Dict:
        """评估深睡眠比例"""
        optimal_min, optimal_max = 15, 25
        
        if deep_percent < 10:
            status = "严重不足"
            color = "red"
        elif deep_percent < 15:
            status = "偏少"
            color = "orange"
        elif deep_percent <= 25:
            status = "理想"
            color = "green"
        else:
            status = "异常偏高"
            color = "yellow"
        
        return {
            "status": status,
            "color": color,
            "optimal_range": f"{optimal_min}-{optimal_max}%"
        }
    
    def _calculate_overall_score(
        self,
        hours: float,
        deep_percent: float,
        quality: int
    ) -> Dict:
        """计算综合睡眠评分"""
        # 各维度权重
        duration_weight = 0.4
        deep_weight = 0.3
        quality_weight = 0.3
        
        # 时长评分 (7-9小时为满分)
        if 7 <= hours <= 9:
            duration_score = 100
        elif hours < 7:
            duration_score = (hours / 7) * 100
        else:
            duration_score = max(60, 100 - (hours - 9) * 10)
        
        # 深睡眠评分
        if 15 <= deep_percent <= 25:
            deep_score = 100
        elif deep_percent < 15:
            deep_score = (deep_percent / 15) * 100
        else:
            deep_score = max(80, 100 - (deep_percent - 25) * 5)
        
        # 质量评分 (转换为百分制)
        quality_score = quality * 10
        
        # 综合评分
        overall = (
            duration_score * duration_weight +
            deep_score * deep_weight +
            quality_score * quality_weight
        )
        
        # 确定等级
        if overall >= 90:
            grade = "A"
            grade_desc = "优秀"
        elif overall >= 80:
            grade = "B"
            grade_desc = "良好"
        elif overall >= 70:
            grade = "C"
            grade_desc = "一般"
        elif overall >= 60:
            grade = "D"
            grade_desc = "较差"
        else:
            grade = "F"
            grade_desc = "很差"
        
        return {
            "score": round(overall, 1),
            "grade": grade,
            "grade_desc": grade_desc,
            "breakdown": {
                "duration": round(duration_score, 1),
                "deep_sleep": round(deep_score, 1),
                "quality": round(quality_score, 1)
            }
        }
    
    def _generate_recommendations(
        self,
        hours: float,
        deep_percent: float,
        quality: int
    ) -> List[str]:
        """生成睡眠建议"""
        recommendations = []
        
        # 时长建议
        if hours < 7:
            recommendations.append(
                f"睡眠时长偏少，建议提前30分钟上床，目标睡眠{hours + (7 - hours):.1f}小时"
            )
        elif hours > 9:
            recommendations.append("睡眠时间偏长，建议固定起床时间，避免周末睡懒觉")
        
        # 深睡眠建议
        if deep_percent < 15:
            recommendations.append(
                "深睡眠偏少，可能影响身体恢复。建议："
            )
            recommendations.append("  - 睡前2小时避免剧烈运动")
            recommendations.append("  - 保持卧室凉爽（18-20°C）")
            recommendations.append("  - 睡前避免咖啡因和酒精")
        
        # 质量建议
        if quality < 7:
            recommendations.append("睡眠质量有待提升：")
            recommendations.append("  - 睡前减少手机、电脑等蓝光设备使用")
            recommendations.append("  - 尝试冥想或深呼吸放松")
            recommendations.append("  - 保持卧室黑暗和安静")
        
        # 综合建议
        if hours >= 7 and deep_percent >= 15 and quality >= 7:
            recommendations.append("睡眠状况良好，继续保持！")
        
        return recommendations
    
    def _generate_stage_chart(
        self,
        total_hours: float,
        deep_percent: float,
        light_percent: float
    ) -> Dict:
        """生成睡眠阶段图表数据"""
        deep_hours = total_hours * (deep_percent / 100)
        rem_hours = total_hours * 0.22  # 估算
        light_hours = total_hours - deep_hours - rem_hours
        
        return {
            "stages": [
                {"name": "深睡眠", "hours": round(deep_hours, 1), "percent": deep_percent, "color": "#2E86AB"},
                {"name": "REM睡眠", "hours": round(rem_hours, 1), "percent": 22, "color": "#A23B72"},
                {"name": "浅睡眠", "hours": round(light_hours, 1), "percent": max(0, 100 - deep_percent - 22), "color": "#F18F01"}
            ],
            "total_hours": total_hours
        }
    
    def get_sleep_recommendations(self, sleep_issues: List[str]) -> Dict:
        """
        根据睡眠问题获取针对性建议
        
        Args:
            sleep_issues: 问题列表，如 ["insomnia", "snoring", "restless"]
        """
        recommendations = {}
        
        if "insomnia" in sleep_issues:
            recommendations["insomnia"] = [
                "固定作息时间，即使周末也不例外",
                "睡前1小时关闭所有屏幕",
                "如果20分钟睡不着，起床做放松活动",
                "避免午睡或限制午睡在20分钟内",
                "睡前2小时避免剧烈运动"
            ]
        
        if "snoring" in sleep_issues:
            recommendations["snoring"] = [
                "侧卧睡眠，避免仰卧",
                "减肥可以减少打鼾",
                "抬高床头约10厘米",
                "使用加湿器保持呼吸道湿润",
                "如严重请咨询医生，可能是睡眠呼吸暂停"
            ]
        
        if "restless" in sleep_issues:
            recommendations["restless"] = [
                "检查是否缺镁，可适量补充",
                "睡前2小时避免咖啡因",
                "保持卧室温度在18-20°C",
                "使用舒适的床垫和枕头",
                "尝试睡前瑜伽或拉伸"
            ]
        
        return recommendations
    
    def calculate_sleep_debt(self, target_hours: float = 8) -> Dict:
        """
        计算睡眠债务
        
        Args:
            target_hours: 目标睡眠时长
            
        Returns:
            睡眠债务计算结果
        """
        return {
            "calculation": f"睡眠债务 = 7天累计(目标睡眠 - 实际睡眠)",
            "formula": "负值表示欠睡，正值表示补觉",
            "recommendation": "每周睡眠债务不应超过5小时"
        }
