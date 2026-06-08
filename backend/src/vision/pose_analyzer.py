"""
姿态分析器 - 使用MediaPipe提取骨骼关键点并计算关节角度
"""

import os
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import matplotlib.pyplot as plt
import matplotlib.patches as patches


# MediaPipe Landmark定义 (33个关键点)
class Landmarks:
    """人体骨骼关键点索引"""
    NOSE = 0
    LEFT_EYE_INNER = 1
    LEFT_EYE = 2
    LEFT_EYE_OUTER = 3
    RIGHT_EYE_INNER = 4
    RIGHT_EYE = 5
    RIGHT_EYE_OUTER = 6
    LEFT_EAR = 7
    RIGHT_EAR = 8
    MOUTH_LEFT = 9
    MOUTH_RIGHT = 10
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_PINKY = 17
    RIGHT_PINKY = 18
    LEFT_INDEX = 19
    RIGHT_INDEX = 20
    LEFT_THUMB = 21
    RIGHT_THUMB = 22
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32


@dataclass
class JointAngles:
    """关节角度数据"""
    trunk_angle: float = 0      # 躯干前倾角
    hip_angle: float = 0        # 髋角
    knee_angle: float = 0       # 膝角
    shoulder_angle: float = 0   # 肩角
    
    def to_dict(self) -> Dict:
        return {
            "trunk_angle": self.trunk_angle,
            "hip_angle": self.hip_angle,
            "knee_angle": self.knee_angle,
            "shoulder_angle": self.shoulder_angle,
        }


@dataclass
class FormAssessment:
    """动作评估结果"""
    quality: str  # excellent, good, fair, poor
    warnings: List[str]
    suggestions: List[str]
    angles: JointAngles
    
    def to_dict(self) -> Dict:
        return {
            "quality": self.quality,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "angles": self.angles.to_dict(),
        }


class PoseAnalyzer:
    """
    姿态分析器
    
    使用MediaPipe提取人体骨骼关键点，计算关节角度，
    评估运动动作质量。
    
    支持:
    - 深蹲角度计算
    - 塌腰检测
    - 膝盖内扣检测
    - 骨骼可视化绘制
    """
    
    # 骨骼连接定义
    POSE_CONNECTIONS = [
        # 躯干
        (Landmarks.LEFT_SHOULDER, Landmarks.RIGHT_SHOULDER),  # 肩
        (Landmarks.LEFT_SHOULDER, Landmarks.LEFT_HIP),        # 左肩到左髋
        (Landmarks.RIGHT_SHOULDER, Landmarks.RIGHT_HIP),      # 右肩到右髋
        (Landmarks.LEFT_HIP, Landmarks.RIGHT_HIP),            # 髋
        
        # 左臂
        (Landmarks.LEFT_SHOULDER, Landmarks.LEFT_ELBOW),
        (Landmarks.LEFT_ELBOW, Landmarks.LEFT_WRIST),
        
        # 右臂
        (Landmarks.RIGHT_SHOULDER, Landmarks.RIGHT_ELBOW),
        (Landmarks.RIGHT_ELBOW, Landmarks.RIGHT_WRIST),
        
        # 左腿
        (Landmarks.LEFT_HIP, Landmarks.LEFT_KNEE),
        (Landmarks.LEFT_KNEE, Landmarks.LEFT_ANKLE),
        (Landmarks.LEFT_ANKLE, Landmarks.LEFT_HEEL),
        (Landmarks.LEFT_HEEL, Landmarks.LEFT_FOOT_INDEX),
        
        # 右腿
        (Landmarks.RIGHT_HIP, Landmarks.RIGHT_KNEE),
        (Landmarks.RIGHT_KNEE, Landmarks.RIGHT_ANKLE),
        (Landmarks.RIGHT_ANKLE, Landmarks.RIGHT_HEEL),
        (Landmarks.RIGHT_HEEL, Landmarks.RIGHT_FOOT_INDEX),
    ]
    
    # 角度阈值
    SQUAT_THRESHOLDS = {
        "knee_ideal_min": 85,
        "knee_ideal_max": 95,
        "knee_warning": 100,  # 超过这个说明膝盖过度前移
        "trunk_ideal_min": 30,
        "trunk_ideal_max": 60,
        "trunk_warning": 70,  # 超过这个说明塌腰
        "hip_ideal_min": 70,
        "hip_ideal_max": 100,
    }
    
    def __init__(self):
        self.mp_pose = None
        self.mp_drawing = None
        self._initialize_mediapipe()
    
    def _initialize_mediapipe(self):
        """初始化MediaPipe"""
        try:
            import mediapipe as mp
            self.mp_pose = mp.solutions.pose
            self.mp_drawing = mp.solutions.drawing_utils
            self.mp_drawing_styles = mp.solutions.drawing_styles
            self._mediapipe_available = True
        except ImportError:
            print("MediaPipe未安装，将使用模拟数据")
            self._mediapipe_available = False
    
    def analyze_video(self, video_path: str) -> Dict:
        """
        分析视频中的姿态
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            分析结果字典
        """
        if not os.path.exists(video_path):
            return {"error": f"视频文件不存在: {video_path}"}
        
        if not self._mediapipe_available:
            return self._generate_mock_analysis()
        
        # 打开视频
        cap = cv2.VideoCapture(video_path)
        frames = []
        all_landmarks = []
        
        with self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            enable_segmentation=True,
            min_detection_confidence=0.5
        ) as pose:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 转换为RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(rgb_frame)
                
                if results.pose_landmarks:
                    all_landmarks.append(results.pose_landmarks)
                    frames.append(frame)
        
        cap.release()
        
        if not frames:
            return {"error": "未检测到人体姿态"}
        
        # 找到深蹲最低点（通常是膝盖角最小的帧）
        min_knee_angle_frame = self._find_lowest_point(all_landmarks, frames)
        
        # 分析该帧的角度
        landmarks = all_landmarks[min_knee_angle_frame["index"]]
        angles = self._calculate_squat_angles(landmarks)
        assessment = self._assess_squat_form(angles)
        
        # 生成骨骼可视化
        skeleton_image = self._draw_skeleton(
            frames[min_knee_angle_frame["index"]],
            landmarks,
            angles,
            assessment
        )
        
        return {
            "success": True,
            "angles": angles.to_dict(),
            "assessment": assessment.to_dict(),
            "key_frame_index": min_knee_angle_frame["index"],
            "skeleton_image": skeleton_image,
            "total_frames": len(frames),
            "warnings": assessment.warnings,
            "suggestions": assessment.suggestions,
        }
    
    def _find_lowest_point(self, landmarks_list: List, frames: List) -> Dict:
        """找到深蹲最低点的帧"""
        min_knee_angle = float('inf')
        min_frame_index = 0
        
        for i, landmarks in enumerate(landmarks_list):
            angles = self._calculate_squat_angles(landmarks)
            if angles.knee_angle < min_knee_angle and angles.knee_angle > 0:
                min_knee_angle = angles.knee_angle
                min_frame_index = i
        
        return {"index": min_frame_index, "knee_angle": min_knee_angle}
    
    def _calculate_squat_angles(self, landmarks) -> JointAngles:
        """计算深蹲相关角度"""
        def get_angle(p1, p2, p3) -> float:
            """计算三点形成的角度"""
            v1 = np.array([p1.x - p2.x, p1.y - p2.y])
            v2 = np.array([p3.x - p2.x, p3.y - p2.y])
            
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
            cos_angle = np.clip(cos_angle, -1, 1)
            angle = np.arccos(cos_angle) * 180 / np.pi
            return float(angle)
        
        # 获取关键点
        lm = landmarks.landmark
        
        # 计算躯干角度 (肩-髋与垂直线的夹角)
        shoulder_mid_x = (lm[Landmarks.LEFT_SHOULDER].x + lm[Landmarks.RIGHT_SHOULDER].x) / 2
        shoulder_mid_y = (lm[Landmarks.LEFT_SHOULDER].y + lm[Landmarks.RIGHT_SHOULDER].y) / 2
        hip_mid_x = (lm[Landmarks.LEFT_HIP].x + lm[Landmarks.RIGHT_HIP].x) / 2
        hip_mid_y = (lm[Landmarks.LEFT_HIP].y + lm[Landmarks.RIGHT_HIP].y) / 2
        
        # 躯干前倾角（与垂直线的夹角）
        trunk_delta_x = shoulder_mid_x - hip_mid_x
        trunk_delta_y = shoulder_mid_y - hip_mid_y
        trunk_angle = abs(np.arctan2(trunk_delta_x, -trunk_delta_y) * 180 / np.pi)
        
        # 髋角 (肩-髋-膝)
        hip_angle = get_angle(
            lm[Landmarks.LEFT_SHOULDER],
            lm[Landmarks.LEFT_HIP],
            lm[Landmarks.LEFT_KNEE]
        )
        
        # 膝角 (髋-膝-踝)
        knee_angle = get_angle(
            lm[Landmarks.LEFT_HIP],
            lm[Landmarks.LEFT_KNEE],
            lm[Landmarks.LEFT_ANKLE]
        )
        
        # 肩角 (髋-肩-肘)
        shoulder_angle = get_angle(
            lm[Landmarks.LEFT_HIP],
            lm[Landmarks.LEFT_SHOULDER],
            lm[Landmarks.LEFT_ELBOW]
        )
        
        return JointAngles(
            trunk_angle=round(trunk_angle, 1),
            hip_angle=round(hip_angle, 1),
            knee_angle=round(knee_angle, 1),
            shoulder_angle=round(shoulder_angle, 1)
        )
    
    def _assess_squat_form(self, angles: JointAngles) -> FormAssessment:
        """评估深蹲动作质量"""
        warnings = []
        suggestions = []
        issues = 0
        
        # 检查膝角
        if angles.knee_angle > self.SQUAT_THRESHOLDS["knee_warning"]:
            warnings.append(f"⚠️ 膝盖过度前移: {angles.knee_angle}° (建议 < {self.SQUAT_THRESHOLDS['knee_ideal_max']}°)")
            suggestions.append("重心放后，臀部向后坐")
            issues += 1
        elif angles.knee_angle < self.SQUAT_THRESHOLDS["knee_ideal_min"]:
            warnings.append(f"⚠️ 膝角过小: {angles.knee_angle}°")
            issues += 1
        
        # 检查躯干角（塌腰检测）
        if angles.trunk_angle > self.SQUAT_THRESHOLDS["trunk_warning"]:
            warnings.append(f"🔴 核心塌腰警告: {angles.trunk_angle}° (建议 < {self.SQUAT_THRESHOLDS['trunk_ideal_max']}°)")
            suggestions.append("收紧腹横肌，保持脊柱中立")
            suggestions.append("建议练习: 猫牛式、死虫式激活核心")
            issues += 2  # 塌腰是严重问题
        elif angles.trunk_angle > self.SQUAT_THRESHOLDS["trunk_ideal_max"]:
            warnings.append(f"⚠️ 躯干前倾过大: {angles.trunk_angle}°")
            issues += 1
        
        # 判断质量等级
        if issues == 0:
            quality = "excellent"
        elif issues == 1:
            quality = "good"
        elif issues <= 2:
            quality = "fair"
        else:
            quality = "poor"
        
        return FormAssessment(
            quality=quality,
            warnings=warnings,
            suggestions=suggestions if suggestions else ["动作基本正确，继续保持！"],
            angles=angles
        )
    
    def _draw_skeleton(
        self,
        frame,
        landmarks,
        angles: JointAngles,
        assessment: FormAssessment
    ) -> np.ndarray:
        """绘制骨骼可视化图"""
        # 创建图像副本
        h, w = frame.shape[:2]
        vis_image = frame.copy()
        
        # 绘制骨骼连接
        for connection in self.POSE_CONNECTIONS:
            start_idx, end_idx = connection
            start = landmarks.landmark[start_idx]
            end = landmarks.landmark[end_idx]
            
            # 根据质量决定颜色
            if assessment.quality == "poor" and any("塌腰" in w for w in assessment.warnings):
                color = (0, 0, 255)  # 红色警告
            elif assessment.quality in ["fair", "good"]:
                color = (0, 165, 255)  # 橙色
            else:
                color = (0, 255, 0)  # 绿色
            
            start_coords = (int(start.x * w), int(start.y * h))
            end_coords = (int(end.x * w), int(end.y * h))
            cv2.line(vis_image, start_coords, end_coords, color, 3)
        
        # 绘制关键点
        key_points = [
            Landmarks.LEFT_HIP, Landmarks.RIGHT_HIP,
            Landmarks.LEFT_KNEE, Landmarks.RIGHT_KNEE,
            Landmarks.LEFT_SHOULDER, Landmarks.RIGHT_SHOULDER
        ]
        for idx in key_points:
            pt = landmarks.landmark[idx]
            coords = (int(pt.x * w), int(pt.y * h))
            cv2.circle(vis_image, coords, 8, (255, 255, 0), -1)
        
        # 添加角度标注
        # 躯干角
        hip = landmarks.landmark[Landmarks.LEFT_HIP]
        shoulder = landmarks.landmark[Landmarks.LEFT_SHOULDER]
        cv2.putText(vis_image, f"躯干: {angles.trunk_angle}°", 
                   (int(hip.x * w) + 20, int(hip.y * h)),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 膝角
        knee = landmarks.landmark[Landmarks.LEFT_KNEE]
        cv2.putText(vis_image, f"膝: {angles.knee_angle}°",
                   (int(knee.x * w) + 20, int(knee.y * h)),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 添加质量标签
        quality_colors = {
            "excellent": (0, 255, 0),
            "good": (0, 255, 255),
            "fair": (0, 165, 255),
            "poor": (0, 0, 255)
        }
        quality_labels = {
            "excellent": "优秀",
            "good": "良好",
            "fair": "一般",
            "poor": "需改进"
        }
        
        label = f"动作质量: {quality_labels[assessment.quality]}"
        color = quality_colors[assessment.quality]
        cv2.putText(vis_image, label, (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
        # 添加警告框
        if assessment.warnings:
            y_offset = 80
            for warning in assessment.warnings[:3]:
                cv2.putText(vis_image, warning, (20, y_offset),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                y_offset += 30
        
        return vis_image
    
    def _generate_mock_analysis(self) -> Dict:
        """生成模拟分析结果（当MediaPipe不可用时）"""
        # 生成模拟角度数据
        angles = JointAngles(
            trunk_angle=35.2,
            hip_angle=85.6,
            knee_angle=92.3,
            shoulder_angle=170.0
        )
        
        assessment = self._assess_squat_form(angles)
        
        return {
            "success": True,
            "simulated": True,
            "angles": angles.to_dict(),
            "assessment": assessment.to_dict(),
            "warnings": assessment.warnings,
            "suggestions": assessment.suggestions,
            "note": "使用模拟数据，请安装MediaPipe获取真实分析"
        }
    
    def generate_angle_plot(self, angles: JointAngles) -> str:
        """生成角度可视化图表"""
        fig, ax = plt.subplots(1, 1, figsize=(8, 4))
        
        categories = ['躯干角度', '髋角度', '膝角度', '肩角度']
        values = [angles.trunk_angle, angles.hip_angle, angles.knee_angle, angles.shoulder_angle]
        
        # 理想范围
        ideal_ranges = [(30, 60), (70, 100), (85, 95), (150, 180)]
        colors = []
        for v, (low, high) in zip(values, ideal_ranges):
            if low <= v <= high:
                colors.append('green')
            else:
                colors.append('red')
        
        bars = ax.barh(categories, values, color=colors, alpha=0.7)
        ax.axvline(x=0, color='black', linewidth=0.5)
        
        # 添加数值标签
        for bar, val in zip(bars, values):
            ax.text(val + 2, bar.get_y() + bar.get_height()/2,
                   f'{val:.1f}°', va='center', fontsize=11)
        
        ax.set_xlim(0, 180)
        ax.set_xlabel('角度 (度)')
        ax.set_title('深蹲关节角度分析', fontsize=14, fontweight='bold')
        
        # 添加图例
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='green', alpha=0.7, label='理想范围'),
            Patch(facecolor='red', alpha=0.7, label='超出范围')
        ]
        ax.legend(handles=legend_elements, loc='lower right')
        
        plt.tight_layout()
        
        # 保存
        os.makedirs("output/charts", exist_ok=True)
        path = "output/charts/squat_angles.png"
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return path
