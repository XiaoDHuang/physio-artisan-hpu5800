"""
语音合成器 - 使用Edge-TTS生成高拟真语音
"""

import os
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import base64
import json


class SpeechSynthesizer:
    """
    Edge-TTS语音合成器
    
    使用Microsoft Edge神经网络语音生成高拟真中文语音
    支持zh-CN-XiaoxiaoNeural等自然女声
    """
    
    def __init__(self, output_dir: str = "output/audio"):
        self.output_dir = output_dir
        self.voice = "zh-CN-XiaoxiaoNeural"
        self.voice_settings = {
            "rate": "+0%",
            "pitch": "+0Hz",
            "volume": "+0%"
        }
        self._edge_tts_available = self._check_edge_tts()
        os.makedirs(output_dir, exist_ok=True)
    
    def _check_edge_tts(self) -> bool:
        """检查edge-tts是否可用"""
        try:
            import edge_tts
            return True
        except ImportError:
            return False
    
    def generate_speech(self, text: str, filename: str = None) -> str:
        """
        生成语音文件
        
        Args:
            text: 要转换的文本
            filename: 保存文件名
            
        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.mp3"
        
        filepath = os.path.join(self.output_dir, filename)
        
        if self._edge_tts_available:
            try:
                asyncio.run(self._generate_async(text, filepath))
            except Exception as e:
                print(f"语音生成失败: {e}")
                return self._create_placeholder(filepath)
        else:
            # 创建设置文件说明
            return self._create_placeholder(filepath)
        
        return filepath
    
    async def _generate_async(self, text: str, filepath: str):
        """异步生成语音"""
        import edge_tts
        
        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self.voice_settings["rate"],
            pitch=self.voice_settings["pitch"],
            volume=self.voice_settings["volume"]
        )
        await communicate.save(filepath)
    
    def _create_placeholder(self, filepath: str) -> str:
        """创建占位文件"""
        with open(filepath.replace(".mp3", ".txt"), "w") as f:
            f.write("语音文件需要edge-tts库支持\n运行: pip install edge-tts")
        return filepath
    
    def generate_health_report(
        self,
        user_name: str,
        health_metrics: Dict,
        recommendations: List[str],
        training_plan: Dict = None,
        meal_plan: Dict = None
    ) -> str:
        """
        生成完整健康报告语音
        
        Args:
            user_name: 用户名
            health_metrics: 健康指标
            recommendations: 建议列表
            training_plan: 训练计划
            meal_plan: 饮食计划
            
        Returns:
            语音文件路径
        """
        # 构建语音文本
        text_parts = [
            f"您好，{user_name}，这里是HPU健康智能体，为您播报今日健康报告。"
        ]
        
        # 健康指标
        if health_metrics:
            text_parts.append(f"今日健康指标：")
            if "body_age" in health_metrics:
                text_parts.append(f"身体年龄约{health_metrics['body_age']}岁。")
            if "bmi" in health_metrics:
                text_parts.append(f"BMI指数为{health_metrics['bmi']}。")
            if "calories_burned" in health_metrics:
                text_parts.append(f"今日已消耗热量约{health_metrics['calories_burned']}千卡。")
        
        # 建议
        if recommendations:
            text_parts.append("以下是今日健康建议：")
            for i, rec in enumerate(recommendations[:3], 1):
                text_parts.append(f"第{i}条，{rec}。")
        
        # 训练计划
        if training_plan:
            focus = training_plan.get("focus", "综合训练")
            text_parts.append(f"今日训练重点是{focus}，建议进行力量训练和有氧运动。")
        
        # 饮食计划
        if meal_plan:
            target = meal_plan.get("target_calories", 2000)
            text_parts.append(f"今日目标热量摄入约{target}千卡，请注意均衡营养。")
        
        text_parts.append("以上是今日健康报告的全部内容，感谢收听，祝您生活愉快！")
        
        full_text = "".join(text_parts)
        
        # 清理文本
        full_text = self._clean_text(full_text)
        
        # 生成语音
        filename = f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        return self.generate_speech(full_text, filename)
    
    def generate_daily_plan_speech(
        self,
        training_plan: Dict,
        meal_plan: Dict
    ) -> str:
        """
        生成今日计划语音
        
        Args:
            training_plan: 训练计划
            meal_plan: 饮食计划
            
        Returns:
            语音文件路径
        """
        parts = ["您好，以下是今日的定制调整计划。"]
        
        if training_plan:
            focus = training_plan.get("focus", "综合训练")
            exercise_type = training_plan.get("type", "混合训练")
            parts.append(f"训练方面：今日重点是{focus}，推荐{exercise_type}，具体动作包括深蹲、硬拉、划船等。")
        
        if meal_plan:
            calories = meal_plan.get("target_calories", 2000)
            macros = meal_plan.get("macros", {})
            parts.append(f"饮食方面：目标热量约{calories}千卡，建议摄入蛋白质约{macros.get('protein_g', 100)}克，碳水化合物约{macros.get('carbs_g', 200)}克，脂肪约{macros.get('fat_g', 60)}克。")
        
        parts.append("请按照计划执行，祝您训练顺利！")
        
        text = self._clean_text("".join(parts))
        filename = f"daily_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        return self.generate_speech(text, filename)
    
    def generate_alert_speech(
        self,
        alert_type: str,
        message: str
    ) -> str:
        """
        生成告警语音
        
        Args:
            alert_type: 告警类型
            message: 告警消息
            
        Returns:
            语音文件路径
        """
        alert_messages = {
            "workout_reminder": "提醒您：今日训练计划还未完成，请在今晚抽出时间进行运动。",
            "nutrition_warning": "提醒您：今日热量摄入已接近目标，请注意控制饮食。",
            "sleep_reminder": "提醒您：现在是休息时间，建议您准备就寝，保证充足睡眠。",
            "hydration": "提醒您：今日饮水量不足，请注意补充水分。",
        }
        
        text = self._clean_text(alert_messages.get(alert_type, message))
        filename = f"alert_{alert_type}_{datetime.now().strftime('%H%M%S')}.mp3"
        return self.generate_speech(text, filename)
    
    def _clean_text(self, text: str) -> str:
        """清理文本以适配语音合成"""
        # 移除emoji
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        text = emoji_pattern.sub('', text)
        
        # 移除特殊符号
        text = text.replace('📊', '').replace('🏃', '').replace('🍽️', '')
        text = text.replace('😴', '').replace('💡', '').replace('⚠️', '')
        text = text.replace('•', '').replace('●', '').replace('○', '')
        text = text.replace('[', '').replace(']', '')
        
        # 清理多余空格
        while '  ' in text:
            text = text.replace('  ', ' ')
        
        return text.strip()
    
    def get_audio_base64(self, filepath: str) -> Optional[str]:
        """获取音频的base64编码（用于网页播放）"""
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'rb') as f:
                audio_data = base64.b64encode(f.read()).decode('utf-8')
            return f"data:audio/mp3;base64,{audio_data}"
        except Exception:
            return None
    
    def list_voices(self) -> List[Dict]:
        """列出可用的语音"""
        if self._edge_tts_available:
            try:
                import asyncio
                import edge_tts
                
                async def get_voices():
                    return await edge_tts.list_voices()
                
                voices = asyncio.run(get_voices())
                chinese = [v for v in voices if v['Locale'].startswith('zh-CN')]
                return [
                    {
                        "name": v['Name'],
                        "language": v['Locale'],
                        "gender": v['Gender']
                    }
                    for v in chinese[:10]
                ]
            except Exception:
                pass
        
        # 默认语音列表
        return [
            {"name": "zh-CN-XiaoxiaoNeural", "language": "zh-CN", "gender": "Female"},
            {"name": "zh-CN-YunxiNeural", "language": "zh-CN", "gender": "Male"},
            {"name": "zh-CN-XiaoyiNeural", "language": "zh-CN", "gender": "Female"},
        ]


import re
