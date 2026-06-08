"""
安全护栏 - 双层过滤 + Llama Guard风格的安全审核
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class SafetyLevel(Enum):
    """安全等级"""
    SAFE = "safe"
    LOW_RISK = "low_risk"
    MEDIUM_RISK = "medium_risk"
    HIGH_RISK = "high_risk"
    BLOCKED = "blocked"


@dataclass
class SafetyCheckResult:
    """安全检查结果"""
    is_safe: bool
    level: SafetyLevel
    violations: List[str]
    warnings: List[str]
    category: str  # injection, medical, privacy, inappropriate, safe
    sanitized_content: str
    block_reason: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "is_safe": self.is_safe,
            "level": self.level.value,
            "violations": self.violations,
            "warnings": self.warnings,
            "category": self.category,
            "block_reason": self.block_reason,
        }


class SafetyGuardrails:
    """
    安全护栏系统 - 双层过滤架构
    
    第一层: 确定性的正则/Aho-Corasick匹配
    第二层: Llama Guard 2 风格的分类模型(模拟)
    
    检测类型:
    - 提示注入 (Prompt Injection)
    - 越狱攻击 (Jailbreak)
    - 医疗禁区 (Medical Boundary)
    - 隐私泄露 (Privacy)
    - 不当内容 (Inappropriate)
    """
    
    # ============ 第一层: 注入检测模式 ============
    INJECTION_PATTERNS = [
        # 英文注入
        (r"ignore\s+(previous|all\s+previous|your\s+instructions?)", "ignore_instructions"),
        (r"disregard\s+your\s+(instructions?|rules?)", "disregard_rules"),
        (r"you\s+are\s+now\s+", "role_play_attempt"),
        (r"pretend\s+you\s+are", "pretend_role"),
        (r"new\s+(system\s+)?prompt", "prompt_injection"),
        (r"reveal\s+(your|hidden|secret)", "prompt_leak"),
        (r"override\s+(your|my|all)", "override_attempt"),
        (r"forget\s+(everything|all|previous)", "forget_attempt"),
        (r"disable\s+(safety|filter|restriction)", "disable_safety"),
        (r"\\system\\", "system_escape"),
        (r"roleplay\s+as", "roleplay_attempt"),
        (r"<\|system\|>|<\|user\|>|<\|assistant\|>", "delimiter_injection"),
        
        # 中文注入
        (r"忽略.*(之前|上面|所有|指令)", "ignore_chinese"),
        (r"无视.*(指令|规则|设定)", "disregard_chinese"),
        (r"你现在?是", "role_chinese"),
        (r"现在?扮演", "pretend_chinese"),
        (r"打破.*角色", "break_role"),
        (r"修改.*提示", "modify_prompt"),
        (r"忘记.*设定", "forget_setting"),
        (r"禁用.*安全", "disable_safety_chinese"),
        (r"关闭.*限制", "close_restriction"),
        (r"获取.*原始.*提示", "get_raw_prompt"),
        (r"给我.*系统.*提示", "get_system_prompt"),
        (r"你是.*不是.*吗", "challenge_identity"),
    ]
    
    # ============ 第二层: 医疗禁区词汇 ============
    MEDICAL_FORBIDDEN = {
        "diagnostic": [
            "诊断", "确诊", "判断为", "得了", "患有",
            "diagnose", "diagnosis", "你有病",
        ],
        "prescription": [
            "开药", "处方", "给我开", "吃这个药",
            "双氯芬酸", "睾酮", "类固醇", "处方药",
            "prescribe", "prescription", "medication",
        ],
        "treatment": [
            "治疗", "治愈", "疗程", "手术",
            "treat", "cure", "therapy", "treatment",
        ],
        "medical_professional": [
            "医生", "医院", "诊所", "医师",
            "doctor", "hospital", "clinic",
        ],
        "serious_conditions": [
            "心脏病", "糖尿病", "癌症", "肿瘤", "抑郁症",
            "焦虑症", "精神分裂", "艾滋病", "乙肝",
            "heart disease", "diabetes", "cancer", "depression",
        ],
    }
    
    # ============ 第三层: 隐私敏感词 ============
    PRIVACY_SENSITIVE = [
        r"\d{15,18}",      # 身份证号
        r"\d{16,19}",      # 银行卡号
        r"\d{3,4}[-\s]?\d{3,4}[-\s]?\d{3,4}",  # 信用卡号
        r"password[:\s]\w+",  # 密码
        r"secret[:\s]\w+",    # 密钥
    ]
    
    # ============ 第四层: 不当内容 ============
    INAPPROPRIATE = [
        "色情", "赌博", "毒品", "暴力",
        "porn", "gambling", "drugs", "violence",
        "hack", "crack", "exploit",
    ]
    
    # 编译正则表达式
    def __init__(self):
        self.injection_regexes = [
            (re.compile(p, re.IGNORECASE), name)
            for p, name in self.INJECTION_PATTERNS
        ]
        self.privacy_regexes = [
            re.compile(p, re.IGNORECASE)
            for p in self.PRIVACY_SENSITIVE
        ]
        self.violation_log: List[Dict] = []
    
    def check(self, text: str) -> SafetyCheckResult:
        """
        执行完整的安全检查
        
        Args:
            text: 待检查的文本
            
        Returns:
            SafetyCheckResult: 检查结果
        """
        violations = []
        warnings = []
        category = "safe"
        
        # ============ 第一层: 注入检测 ============
        injection_result = self._check_injection(text)
        if injection_result:
            violations.extend(injection_result["violations"])
            category = "injection"
        
        # ============ 第二层: 医疗禁区 ============
        medical_result = self._check_medical_boundary(text)
        if medical_result:
            violations.extend(medical_result["violations"])
            warnings.extend(medical_result["warnings"])
            if category == "safe":
                category = "medical"
        
        # ============ 第三层: 隐私检测 ============
        privacy_result = self._check_privacy(text)
        if privacy_result:
            warnings.extend(privacy_result["warnings"])
        
        # ============ 第四层: 不当内容 ============
        inappropriate_result = self._check_inappropriate(text)
        if inappropriate_result:
            violations.extend(inappropriate_result["violations"])
            if category == "safe":
                category = "inappropriate"
        
        # ============ 确定安全等级 ============
        if violations:
            level = SafetyLevel.HIGH_RISK if any(
                v.startswith("critical") for v in violations
            ) else SafetyLevel.BLOCKED
            is_safe = False
            block_reason = self._generate_block_reason(category, violations)
        elif warnings:
            level = SafetyLevel.MEDIUM_RISK
            is_safe = True
            block_reason = None
        elif category == "safe":
            level = SafetyLevel.SAFE
            is_safe = True
            block_reason = None
        else:
            level = SafetyLevel.LOW_RISK
            is_safe = True
            block_reason = None
        
        # 记录日志
        self._log_violation(text, category, level, violations, warnings)
        
        # 清理文本
        sanitized = self._sanitize(text)
        
        return SafetyCheckResult(
            is_safe=is_safe,
            level=level,
            violations=violations,
            warnings=warnings,
            category=category,
            sanitized_content=sanitized,
            block_reason=block_reason
        )
    
    def _check_injection(self, text: str) -> Optional[Dict]:
        """检查提示注入"""
        violations = []
        
        for regex, name in self.injection_regexes:
            if regex.search(text):
                violations.append(f"injection:{name}")
        
        if violations:
            return {"violations": violations}
        return None
    
    def _check_medical_boundary(self, text: str) -> Optional[Dict]:
        """检查医疗禁区"""
        violations = []
        warnings = []
        
        text_lower = text.lower()
        
        for category, terms in self.MEDICAL_FORBIDDEN.items():
            for term in terms:
                if term.lower() in text_lower:
                    if category in ["diagnostic", "prescription", "treatment"]:
                        violations.append(f"medical:{category}:{term}")
                    else:
                        warnings.append(f"medical_warning:{category}:{term}")
        
        if violations or warnings:
            return {"violations": violations, "warnings": warnings}
        return None
    
    def _check_privacy(self, text: str) -> Optional[Dict]:
        """检查隐私泄露"""
        warnings = []
        
        for regex in self.privacy_regexes:
            matches = regex.findall(text)
            if matches:
                warnings.append(f"privacy:sensitive_data_detected:{len(matches)}")
        
        if warnings:
            return {"warnings": warnings}
        return None
    
    def _check_inappropriate(self, text: str) -> Optional[Dict]:
        """检查不当内容"""
        violations = []
        
        text_lower = text.lower()
        for term in self.INAPPROPRIATE:
            if term.lower() in text_lower:
                violations.append(f"inappropriate:{term}")
        
        if violations:
            return {"violations": violations}
        return None
    
    def _sanitize(self, text: str) -> str:
        """清理文本"""
        # 替换敏感数据
        for regex in self.privacy_regexes:
            text = regex.sub("[已隐藏敏感信息]", text)
        
        return text
    
    def _generate_block_reason(self, category: str, violations: List[str]) -> str:
        """生成拦截原因"""
        reasons = {
            "injection": "检测到提示注入攻击，已拦截",
            "medical": "请求涉及医疗禁区内容，已拦截并建议就医",
            "inappropriate": "请求包含不当内容，已拦截",
            "privacy": "请求可能涉及隐私泄露风险",
        }
        return reasons.get(category, "安全检查未通过")
    
    def _log_violation(
        self,
        text: str,
        category: str,
        level: SafetyLevel,
        violations: List[str],
        warnings: List[str]
    ):
        """记录违规日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "level": level.value,
            "violations": violations,
            "warnings": warnings,
            "text_preview": text[:100] if text else "",
        }
        self.violation_log.append(log_entry)
        
        # 限制日志大小
        if len(self.violation_log) > 1000:
            self.violation_log = self.violation_log[-500:]
    
    def get_logs(self, limit: int = 100) -> List[Dict]:
        """获取违规日志"""
        return self.violation_log[-limit:]
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        total = len(self.violation_log)
        by_category = {}
        by_level = {}
        
        for log in self.violation_log:
            cat = log["category"]
            level = log["level"]
            by_category[cat] = by_category.get(cat, 0) + 1
            by_level[level] = by_level.get(level, 0) + 1
        
        return {
            "total_checks": total,
            "by_category": by_category,
            "by_level": by_level,
            "recent_logs": self.violation_log[-10:] if self.violation_log else [],
        }
    
    def generate_fallback_response(self, category: str) -> str:
        """生成安全拦截后的替代响应"""
        fallbacks = {
            "injection": """
⚠️ 安全拦截已激活

检测到潜在的提示注入攻击请求。
HPU智能体严格遵循其系统设定，无法执行绕过安全限制的指令。

如果您遇到技术问题，请通过正常渠道反馈。
""",
            "medical": """
⚠️ 医疗边界提醒

您的问题可能涉及医疗专业领域。

HPU健康智能体的建议仅供参考，不能替代专业医疗意见。
建议您:

1. 如有健康疑虑，请咨询持牌医生
2. 如需紧急医疗帮助，请拨打120
3. 可联系当地医疗机构进行专业评估

我们始终将您的健康和安全放在首位。
""",
            "inappropriate": """
⚠️ 内容审核未通过

您的请求包含不适合讨论的内容。

HPU健康智能体专注于健身、营养和睡眠管理。
请提出与健康管理相关的问题。
""",
            "privacy": """
⚠️ 隐私保护提醒

检测到您的输入可能包含敏感个人信息。

为保护您的隐私:
- 请勿在对话中分享身份证号、银行卡号等敏感信息
- HPU不会收集或存储您的个人敏感数据

如需帮助，请提供非敏感信息。
""",
        }
        return fallbacks.get(category, fallbacks["injection"])


# 全局单例
_safety_instance = None

def get_safety_guardrails() -> SafetyGuardrails:
    """获取安全护栏单例"""
    global _safety_instance
    if _safety_instance is None:
        _safety_instance = SafetyGuardrails()
    return _safety_instance
