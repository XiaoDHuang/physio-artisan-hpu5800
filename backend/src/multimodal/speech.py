"""
语音合成器
生成健康报告语音播报
"""

import os
from typing import Dict, Optional
from datetime import datetime
import base64

# 尝试导入语音合成库
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False


class SpeechSynthesizer:
    """健康报告语音合成器"""
    
    def __init__(self, output_dir: str = "./output/audio"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.voice = "zh-CN-XiaoxiaoNeural"  # 默认中文女声
    
    async def _generate_audio_async(self, text: str, filename: str) -> str:
        """异步生成音频文件"""
        if not EDGE_TTS_AVAILABLE:
            return self._generate_placeholder_path(filename)
        
        filepath = os.path.join(self.output_dir, filename)
        
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(filepath)
        
        return filepath
    
    def _generate_placeholder_path(self, filename: str) -> str:
        """生成占位符路径"""
        return f"{self.output_dir}/{filename}"
    
    def generate_report(self, health_data, analysis: Dict) -> str:
        """
        生成健康报告语音文本
        
        Args:
            health_data: 健康数据
            analysis: 分析结果
            
        Returns:
            语音报告文本
        """
        date_str = health_data.date or datetime.now().strftime("%Y年%m月%d日")
        
        report_text = f"""
您好，这里是HPU健康智能体，为您播报{date_str}的健康报告。

首先是运动数据：今日步数{health_data.steps}步，
运动时长{health_data.exercise_minutes}分钟，
共消耗热量约{health_data.calories_burned}千卡。

饮食方面：今日摄入热量约{health_data.calories_intake}千卡，
蛋白质{health_data.protein_g}克，碳水化合物{health_data.carbs_g}克，脂肪{health_data.fat_g}克。

睡眠状况：睡眠时长{health_data.sleep_hours}小时，
深睡比例{health_data.deep_sleep_percent}%，睡眠质量评分{health_data.sleep_quality}分。

健康指标方面：您的BMI指数为{analysis.get('bmi', 'N/A')}，
基础代谢率约为{analysis.get('bmr', 'N/A')}千卡每天，
估算身体年龄约为{analysis.get('body_age', 'N/A')}岁。

综合健康评分为{analysis.get('body_age', 70)}分，
状态良好，请继续保持。

以上是今日健康报告的语音播报，
更多详细信息请查看可视化图表。
感谢您的聆听，祝您生活愉快！
"""
        
        return self._clean_text_for_speech(report_text)
    
    def generate_recommendations_speech(self, recommendations: list) -> str:
        """
        生成建议语音
        
        Args:
            recommendations: 建议列表
            
        Returns:
            语音建议文本
        """
        if not recommendations:
            return "目前没有需要特别提醒的事项，请继续保持良好的生活习惯。"
        
        speech = "以下是今日的健康建议："
        
        for i, rec in enumerate(recommendations, 1):
            # 清理建议文本，移除特殊字符
            clean_rec = self._clean_text_for_speech(rec)
            speech += f"第{i}条，{clean_rec}。"
        
        speech += "以上就是今天的建议，祝您健康！"
        return speech
    
    def generate_weekly_summary_speech(self, weekly_data: Dict) -> str:
        """
        生成周报语音
        
        Args:
            weekly_data: 周数据汇总
        """
        avg_steps = weekly_data.get('avg_steps', 8000)
        avg_exercise = weekly_data.get('avg_exercise', 45)
        avg_sleep = weekly_data.get('avg_sleep', 7.5)
        total_workouts = weekly_data.get('total_workouts', 4)
        
        speech = f"""
您好，这是您的本周健康周报。

本周数据汇总：平均每日步数约{avg_steps}步，
平均每日运动时长约{avg_exercise}分钟，
平均每日睡眠时长约{avg_sleep}小时。
本周共完成{total_workouts}次训练。

总体来看，您的健康状况保持良好。
建议下周继续保持当前的运动和饮食习惯。

如果您需要调整训练计划或有其他问题，
请随时告诉我。

感谢使用HPU健康智能体，祝您周末愉快！
"""
        return self._clean_text_for_speech(speech)
    
    def generate_alert_speech(self, alert_type: str, details: Dict) -> str:
        """
        生成提醒语音
        
        Args:
            alert_type: 提醒类型
            details: 详情
        """
        alerts = {
            "low_water": f"提醒您：今日饮水量不足，当前仅为{details.get('current', 0)}毫升，\
建议再补充约{details.get('needed', 1500)}毫升水。",
            
            "missed_workout": f"提醒：今天还没有完成训练计划，\
建议在今晚抽出{details.get('duration', 45)}分钟进行运动。",
            
            "poor_sleep": f"提醒：昨晚睡眠质量评分较低，仅为{details.get('score', 5)}分。\
建议今晚提前30分钟上床休息。",
            
            "calorie_excess": f"提醒：今日已摄入约{details.get('calories', 2000)}千卡热量，\
已超过目标，建议减少{details.get('excess', 200)}千卡的摄入。",
            
            "high_stress": f"健康提醒：检测到您近期的压力水平较高，\
建议增加放松活动，如冥想或轻度运动。"
        }
        
        base_alert = alerts.get(alert_type, "这是一条健康提醒。")
        return self._clean_text_for_speech(base_alert)
    
    async def save_speech_async(self, text: str, filename: str = None) -> str:
        """
        异步保存语音文件
        
        Args:
            text: 要转换的文本
            filename: 保存文件名
            
        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"speech_{timestamp}.mp3"
        
        return await self._generate_audio_async(text, filename)
    
    def save_speech(self, text: str, filename: str = None) -> str:
        """
        同步保存语音文件（使用默认实现）
        
        Args:
            text: 要转换的文本
            filename: 保存文件名
            
        Returns:
            保存的文件路径
        """
        import asyncio
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"speech_{timestamp}.mp3"
        
        if EDGE_TTS_AVAILABLE:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            return loop.run_until_complete(self._generate_audio_async(text, filename))
        else:
            return self._generate_placeholder_path(filename)
    
    def get_audio_as_base64(self, audio_path: str) -> Optional[str]:
        """将音频转换为base64编码（用于网页播放）"""
        if not os.path.exists(audio_path):
            return None
        
        with open(audio_path, 'rb') as f:
            audio_data = base64.b64encode(f.read()).decode('utf-8')
        
        return f"data:audio/mp3;base64,{audio_data}"
    
    def _clean_text_for_speech(self, text: str) -> str:
        """
        清理文本以适配语音合成
        移除或替换无法朗读的字符
        """
        # 移除特殊符号
        text = text.replace('📊', '').replace('🏃', '').replace('🍽️', '')
        text = text.replace('😴', '').replace('💡', '').replace('⚠️', '')
        text = text.replace('•', '').replace('●', '').replace('○', '')
        text = text.replace('━', '').replace('━', '')
        
        # 清理多余空格
        while '  ' in text:
            text = text.replace('  ', ' ')
        
        # 规范化数字朗读
        text = self._format_numbers(text)
        
        return text.strip()
    
    def _format_numbers(self, text: str) -> str:
        """格式化数字以便于语音朗读"""
        import re
        
        # 匹配 kcal 或 千卡
        text = re.sub(r'(\d+)\s*kcal', r'\1千卡', text)
        
        # 匹配 kg 或 公斤
        text = re.sub(r'(\d+\.?\d*)\s*kg', r'\1公斤', text)
        
        # 匹配 cm 或 厘米
        text = re.sub(r'(\d+\.?\d*)\s*cm', r'\1厘米', text)
        
        # 匹配百分数
        text = re.sub(r'(\d+\.?\d*)\s*%', r'\1百分之', text)
        
        # 格式化时间
        text = re.sub(r'(\d+)\s*分钟', r'\1分钟', text)
        text = re.sub(r'(\d+\.?\d*)\s*小时', r'\1小时', text)
        
        return text
    
    def get_available_voices(self) -> list:
        """获取可用的语音列表"""
        if not EDGE_TTS_AVAILABLE:
            return [
                {"name": "zh-CN-XiaoxiaoNeural", "language": "zh-CN", "gender": "Female"},
                {"name": "zh-CN-YunxiNeural", "language": "zh-CN", "gender": "Male"}
            ]
        
        try:
            import asyncio
            voices = asyncio.run(edge_tts.list_voices())
            chinese_voices = [
                v for v in voices 
                if v['Locale'].startswith('zh-CN')
            ]
            return chinese_voices[:10]  # 返回前10个
        except Exception:
            return [
                {"name": "zh-CN-XiaoxiaoNeural", "language": "zh-CN", "gender": "Female"}
            ]
