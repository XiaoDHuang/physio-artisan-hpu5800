"""
图表生成器
使用matplotlib生成健康数据可视化图表
"""

import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import base64
from io import BytesIO

# 尝试导入matplotlib，如果失败则使用备用方案
try:
    import matplotlib
    matplotlib.use('Agg')  # 非交互式后端
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class ChartGenerator:
    """健康数据图表生成器"""
    
    # 颜色方案
    COLORS = {
        "primary": "#2E86AB",      # 深蓝
        "secondary": "#A23B72",    # 紫红
        "success": "#28A745",      # 绿色
        "warning": "#FFC107",      # 黄色
        "danger": "#DC3545",       # 红色
        "info": "#17A2B8",         # 浅蓝
        "neutral": "#6C757D",      # 灰色
        "exercise": "#FF6B35",     # 橙色
        "nutrition": "#7CB518",    # 草绿
        "sleep": "#7209B7"         # 紫色
    }
    
    def __init__(self, output_dir: str = "./output/charts"):
        self.output_dir = output_dir
        if MATPLOTLIB_AVAILABLE:
            self._setup_style()
            os.makedirs(output_dir, exist_ok=True)
    
    def _setup_style(self):
        """设置图表样式"""
        plt.style.use('seaborn-v0_8-whitegrid')
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['figure.facecolor'] = 'white'
    
    def _save_chart(self, fig, filename: str) -> str:
        """保存图表并返回路径"""
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_path(filename)
        
        filepath = os.path.join(self.output_dir, filename)
        fig.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        return filepath
    
    def _generate_placeholder_path(self, filename: str) -> str:
        """生成占位符路径（当matplotlib不可用时）"""
        return f"{self.output_dir}/{filename}"
    
    def generate_report_chart(self, health_data, analysis: Dict) -> List[str]:
        """
        生成综合健康报告图表
        
        Args:
            health_data: 健康数据对象
            analysis: 分析结果
            
        Returns:
            生成的图表文件路径列表
        """
        paths = []
        
        # 1. 生成雷达图 - 综合健康指标
        radar_path = self._generate_radar_chart(analysis)
        paths.append(radar_path)
        
        # 2. 生成趋势图 - 一周数据（模拟）
        trend_path = self._generate_trend_chart(health_data)
        paths.append(trend_path)
        
        # 3. 生成营养分布饼图
        nutrition_path = self._generate_nutrition_chart(health_data)
        paths.append(nutrition_path)
        
        return paths
    
    def _generate_radar_chart(self, analysis: Dict) -> str:
        """生成雷达图 - 多维度健康指标"""
        if not MATPLOTLIB_AVAILABLE:
            return "radar_chart_placeholder.png"
        
        # 准备数据（归一化到0-100）
        categories = ['运动', '营养', '睡眠', '恢复', '心肺', '柔韧']
        
        # 计算各维度得分（这里简化处理）
        scores = [
            min(100, analysis.get('exercise_score', 70)),
            min(100, analysis.get('nutrition_score', 75)),
            min(100, analysis.get('sleep_score', 80)),
            min(100, analysis.get('recovery_score', 75)),
            min(100, analysis.get('cardio_score', 70)),
            min(100, analysis.get('flexibility_score', 65))
        ]
        
        # 补全到6个维度
        while len(scores) < 6:
            scores.append(70)
        scores = scores[:6]
        
        # 创建雷达图
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
        
        # 计算角度
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        scores_plot = scores + [scores[0]]
        angles += angles[:1]
        
        # 绘制
        ax.plot(angles, scores_plot, 'o-', linewidth=2, color=self.COLORS["primary"])
        ax.fill(angles, scores_plot, alpha=0.25, color=self.COLORS["primary"])
        
        # 设置标签
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=12, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=9)
        
        # 添加标题
        plt.title('健康指标雷达图', fontsize=16, fontweight='bold', pad=20)
        
        # 添加中心数据
        center_text = f"综合得分\n{np.mean(scores):.0f}"
        ax.text(0.5, 0.5, center_text, transform=ax.transAxes,
                fontsize=14, ha='center', va='center',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        return self._save_chart(fig, f"radar_chart_{datetime.now().strftime('%Y%m%d')}.png")
    
    def _generate_trend_chart(self, health_data) -> str:
        """生成趋势图 - 展示一周数据变化"""
        if not MATPLOTLIB_AVAILABLE:
            return "trend_chart_placeholder.png"
        
        # 模拟一周数据
        days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        
        # 生成合理的模拟数据
        np.random.seed(42)
        exercise = [45, 0, 55, 30, 60, 90, 40]  # 运动分钟
        calories = [2100, 1950, 2200, 1800, 2300, 2500, 2000]  # 摄入热量
        sleep = [7.5, 6.5, 8.0, 7.0, 7.5, 8.5, 7.2]  # 睡眠时长
        
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12))
        
        # 运动趋势
        bars1 = ax1.bar(days, exercise, color=self.COLORS["exercise"], alpha=0.8)
        ax1.set_ylabel('分钟', fontsize=11)
        ax1.set_title('每日运动时长', fontsize=14, fontweight='bold')
        ax1.axhline(y=60, color=self.COLORS["success"], linestyle='--', label='目标60分钟')
        ax1.legend()
        for bar, val in zip(bars1, exercise):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                    f'{val}', ha='center', va='bottom', fontsize=10)
        
        # 热量趋势
        bars2 = ax2.bar(days, calories, color=self.COLORS["nutrition"], alpha=0.8)
        ax2.set_ylabel('kcal', fontsize=11)
        ax2.set_title('每日摄入热量', fontsize=14, fontweight='bold')
        ax2.axhline(y=2000, color=self.COLORS["warning"], linestyle='--', label='目标2000kcal')
        ax2.legend()
        for bar, val in zip(bars2, calories):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20,
                    f'{val}', ha='center', va='bottom', fontsize=9)
        
        # 睡眠趋势
        line3, = ax3.plot(days, sleep, 'o-', color=self.COLORS["sleep"],
                          linewidth=2, markersize=10)
        ax3.set_ylabel('小时', fontsize=11)
        ax3.set_title('每日睡眠时长', fontsize=14, fontweight='bold')
        ax3.axhline(y=8, color=self.COLORS["success"], linestyle='--', label='目标8小时')
        ax3.fill_between(days, sleep, alpha=0.3, color=self.COLORS["sleep"])
        ax3.legend()
        ax3.set_ylim(0, 10)
        
        plt.suptitle('一周健康数据趋势', fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()
        
        return self._save_chart(fig, f"trend_chart_{datetime.now().strftime('%Y%m%d')}.png")
    
    def _generate_nutrition_chart(self, health_data) -> str:
        """生成营养分布图"""
        if not MATPLOTLIB_AVAILABLE:
            return "nutrition_chart_placeholder.png"
        
        # 模拟营养数据
        protein_g = 80  # 蛋白质克数
        carbs_g = 200   # 碳水克数
        fat_g = 60      # 脂肪克数
        
        # 转换为热量比例
        protein_cal = protein_g * 4
        carbs_cal = carbs_g * 4
        fat_cal = fat_g * 9
        total_cal = protein_cal + carbs_cal + fat_cal
        
        sizes = [protein_cal/total_cal*100, carbs_cal/total_cal*100, fat_cal/total_cal*100]
        labels = [f'蛋白质\n{protein_g}g', f'碳水\n{carbs_g}g', f'脂肪\n{fat_g}g']
        colors = [self.COLORS["primary"], self.COLORS["success"], self.COLORS["warning"]]
        explode = (0.05, 0.02, 0.02)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # 饼图
        wedges, texts, autotexts = ax1.pie(sizes, explode=explode, labels=labels,
                                           colors=colors, autopct='%1.1f%%',
                                           shadow=True, startangle=90)
        for autotext in autotexts:
            autotext.set_fontsize(11)
            autotext.set_fontweight('bold')
        ax1.set_title('营养素热量占比', fontsize=14, fontweight='bold')
        
        # 条形图
        nutrients = ['蛋白质', '碳水', '脂肪']
        values = [protein_g, carbs_g, fat_g]
        colors_bar = [self.COLORS["primary"], self.COLORS["success"], self.COLORS["warning"]]
        
        bars = ax2.bar(nutrients, values, color=colors_bar, alpha=0.8, edgecolor='black')
        ax2.set_ylabel('克数 (g)', fontsize=11)
        ax2.set_title('宏量营养素摄入量', fontsize=14, fontweight='bold')
        ax2.set_ylim(0, max(values) * 1.2)
        
        for bar, val in zip(bars, values):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 3,
                    f'{val}g', ha='center', va='bottom', fontsize=12, fontweight='bold')
        
        # 添加热量标注
        total_calories = protein_cal + carbs_cal + fat_cal
        fig.suptitle(f'饮食分析 | 总热量: {int(total_calories)} kcal',
                    fontsize=16, fontweight='bold', y=1.02)
        
        plt.tight_layout()
        return self._save_chart(fig, f"nutrition_chart_{datetime.now().strftime('%Y%m%d')}.png")
    
    def generate_body_metrics_chart(self, bmi: float, bmr: int, tdee: int) -> str:
        """生成身体指标图表"""
        if not MATPLOTLIB_AVAILABLE:
            return "body_metrics_placeholder.png"
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # BMI条形图
        categories = ['偏瘦', '正常', '超重', '肥胖']
        thresholds = [18.5, 24, 28]
        
        # 创建BMI区间颜色
        colors = []
        if bmi < 18.5:
            colors = [self.COLORS["info"]] * 4
        elif bmi < 24:
            colors = [self.COLORS["neutral"], self.COLORS["success"], self.COLORS["neutral"], self.COLORS["neutral"]]
        elif bmi < 28:
            colors = [self.COLORS["neutral"]] * 2 + [self.COLORS["warning"]] + [self.COLORS["neutral"]]
        else:
            colors = [self.COLORS["neutral"]] * 3 + [self.COLORS["danger"]]
        
        y_pos = [0, 1, 2, 3]
        ax.barh(y_pos, [18.5, 5.5, 4, 12], color=colors, alpha=0.5, height=0.6)
        ax.axvline(x=bmi, color=self.COLORS["secondary"], linewidth=3,
                   label=f'您的BMI: {bmi:.1f}')
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(categories, fontsize=12)
        ax.set_xlabel('BMI值', fontsize=12)
        ax.set_title('BMI身体质量指数', fontsize=16, fontweight='bold')
        ax.legend(loc='upper right', fontsize=11)
        
        # 添加注释
        ax.text(bmi + 0.5, 3.5, f'BMI = {bmi:.1f}', fontsize=12,
                fontweight='bold', color=self.COLORS["secondary"])
        
        # 添加代谢信息文本框
        textstr = f'基础代谢率: {bmr} kcal/天\n每日消耗: {tdee} kcal/天'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=11,
                verticalalignment='top', bbox=props)
        
        plt.tight_layout()
        return self._save_chart(fig, f"body_metrics_{datetime.now().strftime('%Y%m%d')}.png")
    
    def generate_sleep_chart(self, sleep_data: Dict) -> str:
        """生成睡眠分析图表"""
        if not MATPLOTLIB_AVAILABLE:
            return "sleep_chart_placeholder.png"
        
        # 睡眠阶段数据
        stages = sleep_data.get('stages', [
            {'name': '深睡眠', 'percent': 20, 'color': self.COLORS["primary"]},
            {'name': 'REM睡眠', 'percent': 22, 'color': self.COLORS["secondary"]},
            {'name': '浅睡眠', 'percent': 58, 'color': self.COLORS["info"]}
        ])
        
        labels = [s['name'] for s in stages]
        sizes = [s['percent'] for s in stages]
        colors = [s['color'] for s in stages]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # 饼图
        wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors,
                                           autopct='%1.1f%%', startangle=90)
        for autotext in autotexts:
            autotext.set_fontsize(12)
            autotext.set_fontweight('bold')
        ax1.set_title('睡眠阶段分布', fontsize=14, fontweight='bold')
        
        # 时长条形图
        hours = [sleep_data.get('total_hours', 7.5)]
        bars = ax2.bar(['睡眠时长'], hours, color=self.COLORS["sleep"], alpha=0.8)
        ax2.axhline(y=8, color=self.COLORS["success"], linestyle='--',
                   linewidth=2, label='推荐8小时')
        ax2.set_ylim(0, 10)
        ax2.set_ylabel('小时', fontsize=11)
        ax2.set_title('睡眠时长', fontsize=14, fontweight='bold')
        ax2.legend()
        
        for bar, val in zip(bars, hours):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                    f'{val}h', ha='center', va='bottom', fontsize=14, fontweight='bold')
        
        plt.suptitle(f'睡眠分析报告 | 总时长: {hours[0]}小时',
                    fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()
        
        return self._save_chart(fig, f"sleep_chart_{datetime.now().strftime('%Y%m%d')}.png")
    
    def generate_comparison_chart(self, current: Dict, previous: Dict) -> str:
        """生成对比图表 - 本周vs上周"""
        if not MATPLOTLIB_AVAILABLE:
            return "comparison_chart_placeholder.png"
        
        metrics = ['BMI', '体脂率%', '肌肉量kg', '睡眠评分', '日均步数']
        
        current_values = [current.get(m, 0) for m in metrics]
        previous_values = [previous.get(m, 0) for m in metrics]
        
        x = np.arange(len(metrics))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        bars1 = ax.bar(x - width/2, previous_values, width, label='上周',
                      color=self.COLORS["neutral"], alpha=0.7)
        bars2 = ax.bar(x + width/2, current_values, width, label='本周',
                      color=self.COLORS["primary"], alpha=0.8)
        
        ax.set_ylabel('数值', fontsize=12)
        ax.set_title('本周 vs 上周 指标对比', fontsize=16, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(metrics, fontsize=11)
        ax.legend(fontsize=11)
        
        # 添加数值标签
        for bar in bars1:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}', ha='center', va='bottom', fontsize=9)
        for bar in bars2:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        return self._save_chart(fig, f"comparison_{datetime.now().strftime('%Y%m%d')}.png")
    
    def get_chart_as_base64(self, chart_path: str) -> Optional[str]:
        """将图表转换为base64编码（用于网页展示）"""
        if not MATPLOTLIB_AVAILABLE or not os.path.exists(chart_path):
            return None
        
        with open(chart_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')
        
        return f"data:image/png;base64,{img_data}"
