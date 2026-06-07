"""
AI Provider 管理器
支持多API路由，不同Agent可使用不同模型
"""

import os
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()


class BaseAIProvider(ABC):
    """AI Provider基类"""
    
    def __init__(self, api_key: str, endpoint: str = None):
        self.api_key = api_key
        self.endpoint = endpoint
    
    @abstractmethod
    def chat(self, messages: list, model: str = None, **kwargs) -> Dict[str, Any]:
        """发送聊天请求"""
        pass
    
    @abstractmethod
    def get_models(self) -> list:
        """获取可用模型列表"""
        pass


class OpenAIProvider(BaseAIProvider):
    """OpenAI API"""
    
    def __init__(self):
        super().__init__(
            api_key=os.getenv('OPENAI_API_KEY', ''),
            endpoint=os.getenv('OPENAI_ENDPOINT', 'https://api.openai.com/v1')
        )
    
    def chat(self, messages: list, model: str = None, **kwargs) -> Dict[str, Any]:
        if not self.api_key:
            return {'error': 'OpenAI API密钥未配置'}
        
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key, base_url=self.endpoint)
            
            response = client.chat.completions.create(
                model=model or os.getenv('OPENAI_MODEL', 'gpt-4'),
                messages=messages,
                **kwargs
            )
            
            return {
                'content': response.choices[0].message.content,
                'model': response.model,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_models(self) -> list:
        return ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo', 'gpt-4o']


class ZhipuProvider(BaseAIProvider):
    """智谱AI (GLM)"""
    
    def __init__(self):
        super().__init__(
            api_key=os.getenv('ZHIPU_API_KEY', ''),
            endpoint='https://open.bigmodel.cn/api/paas/v4'
        )
    
    def chat(self, messages: list, model: str = None, **kwargs) -> Dict[str, Any]:
        if not self.api_key:
            return {'error': '智谱AI API密钥未配置'}
        
        try:
            from zhipuai import ZhipuAI
            client = ZhipuAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model=model or os.getenv('ZHIPU_MODEL', 'glm-4'),
                messages=messages,
                **kwargs
            )
            
            return {
                'content': response.choices[0].message.content,
                'model': response.model,
                'usage': response.usage.total_tokens
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_models(self) -> list:
        return ['glm-4', 'glm-4-plus', 'glm-4v', 'glm-3-turbo']


class AnthropicProvider(BaseAIProvider):
    """Anthropic (Claude)"""
    
    def __init__(self):
        super().__init__(
            api_key=os.getenv('ANTHROPIC_API_KEY', ''),
            endpoint='https://api.anthropic.com/v1'
        )
    
    def chat(self, messages: list, model: str = None, **kwargs) -> Dict[str, Any]:
        if not self.api_key:
            return {'error': 'Anthropic API密钥未配置'}
        
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            
            # 转换消息格式
            system = ""
            converted_messages = []
            for msg in messages:
                if msg.get('role') == 'system':
                    system = msg.get('content', '')
                else:
                    converted_messages.append({
                        'role': msg.get('role', 'user'),
                        'content': msg.get('content', '')
                    })
            
            response = client.messages.create(
                model=model or os.getenv('ANTHROPIC_MODEL', 'claude-3-opus-20240229'),
                system=system,
                messages=converted_messages,
                **kwargs
            )
            
            return {
                'content': response.content[0].text,
                'model': response.model,
                'usage': {
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_models(self) -> list:
        return ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307']


class AzureOpenAIProvider(BaseAIProvider):
    """Azure OpenAI"""
    
    def __init__(self):
        super().__init__(
            api_key=os.getenv('AZURE_API_KEY', ''),
            endpoint=os.getenv('AZURE_ENDPOINT', '')
        )
    
    def chat(self, messages: list, model: str = None, **kwargs) -> Dict[str, Any]:
        if not self.api_key or not self.endpoint:
            return {'error': 'Azure OpenAI 配置不完整'}
        
        try:
            from openai import AzureOpenAI
            client = AzureOpenAI(
                api_key=self.api_key,
                api_version="2024-02-01",
                azure_endpoint=self.endpoint
            )
            
            deployment = os.getenv('AZURE_DEPLOYMENT', 'gpt-4')
            
            response = client.chat.completions.create(
                model=deployment,
                messages=messages,
                **kwargs
            )
            
            return {
                'content': response.choices[0].message.content,
                'model': deployment,
                'usage': response.usage.total_tokens
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_models(self) -> list:
        return ['gpt-4', 'gpt-35-turbo']  # 取决于Azure部署


class MockProvider(BaseAIProvider):
    """模拟Provider（用于测试）"""
    
    def __init__(self):
        super().__init__(api_key='mock', endpoint='')
    
    def chat(self, messages: list, model: str = None, **kwargs) -> Dict[str, Any]:
        last_message = messages[-1]['content'] if messages else ''
        
        # 根据内容返回模拟响应
        responses = {
            '训练': '好的，我为您制定训练计划：深蹲4组、硬拉3组、腿举3组...',
            '饮食': '基于您的目标，建议每日摄入2000kcal，蛋白质160g...',
            '睡眠': '您的睡眠质量良好，建议保持7-8小时睡眠...'
        }
        
        for key, response in responses.items():
            if key in last_message:
                return {
                    'content': response,
                    'model': 'mock-gpt',
                    'usage': {'total_tokens': 100}
                }
        
        return {
            'content': f'我收到您的消息了: {last_message[:50]}... 作为模拟Agent，我暂时无法处理复杂请求。',
            'model': 'mock-gpt',
            'usage': {'total_tokens': 50}
        }
    
    def get_models(self) -> list:
        return ['mock-gpt']


class CustomProvider(BaseAIProvider):
    """自定义API Provider（支持任何兼容OpenAI格式的API）"""

    def __init__(self, index: int):
        super().__init__(
            api_key=os.getenv(f'CUSTOM_{index}_API_KEY', ''),
            endpoint=os.getenv(f'CUSTOM_{index}_ENDPOINT', '')
        )
        self.name = os.getenv(f'CUSTOM_{index}_NAME', f'Custom {index}')
        self.models_str = os.getenv(f'CUSTOM_{index}_MODELS', '')
        self.models = [m.strip() for m in self.models_str.split(',') if m.strip()]

    def chat(self, messages: list, model: str = None, **kwargs) -> Dict[str, Any]:
        if not self.api_key or not self.endpoint:
            return {'error': f'{self.name} API密钥或端点未配置'}

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.endpoint)

            response = client.chat.completions.create(
                model=model or (self.models[0] if self.models else 'custom-model'),
                messages=messages,
                **kwargs
            )

            return {
                'content': response.choices[0].message.content,
                'model': response.model,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
        except Exception as e:
            return {'error': str(e)}

    def get_models(self) -> list:
        return self.models if self.models else ['custom-model']


class AIManager:
    """
    AI管理器
    统一管理多个AI Provider，支持不同Agent使用不同模型
    """
    
    # Agent与Provider的默认绑定
    DEFAULT_AGENT_PROVIDER = {
        'HPUAssistant': 'openai',
        'StateEvaluator': 'zhipu',
        'ExerciseCoach': 'openai',
        'NutritionPlanner': 'zhipu',
        'GuardrailAuditor': 'anthropic',
    }
    
    # Agent与模型的默认绑定
    DEFAULT_AGENT_MODEL = {
        'HPUAssistant': 'gpt-4',
        'StateEvaluator': 'glm-4',
        'ExerciseCoach': 'gpt-4-turbo',
        'NutritionPlanner': 'glm-4-plus',
        'GuardrailAuditor': 'claude-3-opus-20240229',
    }
    
    def __init__(self):
        self.providers = {
            'openai': OpenAIProvider(),
            'zhipu': ZhipuProvider(),
            'anthropic': AnthropicProvider(),
            'azure': AzureOpenAIProvider(),
            'mock': MockProvider(),
        }

        # 加载自定义API Provider
        self._load_custom_providers()

        # 从环境变量加载Agent绑定配置
        self.agent_provider = self._load_agent_provider_config()
        self.agent_model = self._load_agent_model_config()

    def _load_custom_providers(self):
        """加载自定义API Provider"""
        for i in range(1, 6):  # CUSTOM_1 到 CUSTOM_5
            if os.getenv(f'CUSTOM_{i}_API_KEY'):
                self.providers[f'custom_{i}'] = CustomProvider(i)
    
    def _load_agent_provider_config(self) -> Dict[str, str]:
        """从环境变量加载Agent-Provider绑定"""
        config = self.DEFAULT_AGENT_PROVIDER.copy()

        for agent in ['HPUAssistant', 'StateEvaluator', 'ExerciseCoach', 'NutritionPlanner', 'GuardrailAuditor']:
            env_key = f'{agent.upper()}_PROVIDER'
            if os.getenv(env_key):
                config[agent] = os.getenv(env_key)

        return config

    def _load_agent_model_config(self) -> Dict[str, str]:
        """从环境变量加载Agent-Model绑定"""
        config = self.DEFAULT_AGENT_MODEL.copy()

        for agent in ['HPUAssistant', 'StateEvaluator', 'ExerciseCoach', 'NutritionPlanner', 'GuardrailAuditor']:
            env_key = f'{agent.upper()}_MODEL'
            if os.getenv(env_key):
                config[agent] = os.getenv(env_key)

        return config

    def register_custom_provider(self, index: int, name: str, api_key: str, endpoint: str, models: list):
        """动态注册自定义Provider"""
        self.providers[f'custom_{index}'] = CustomProvider(index)
    
    def get_provider(self, name: str) -> Optional[BaseAIProvider]:
        """获取Provider"""
        return self.providers.get(name)
    
    def get_provider_for_agent(self, agent_name: str) -> BaseAIProvider:
        """获取Agent对应的Provider"""
        provider_name = self.agent_provider.get(agent_name, 'mock')
        return self.providers.get(provider_name, self.providers['mock'])
    
    def get_model_for_agent(self, agent_name: str) -> str:
        """获取Agent对应的模型"""
        return self.agent_model.get(agent_name, 'gpt-4')
    
    def chat(self, agent_name: str, messages: list, **kwargs) -> Dict[str, Any]:
        """使用指定Agent的Provider和模型进行对话"""
        provider = self.get_provider_for_agent(agent_name)
        model = kwargs.pop('model', None) or self.get_model_for_agent(agent_name)
        
        return provider.chat(messages, model=model, **kwargs)
    
    def set_agent_provider(self, agent_name: str, provider_name: str):
        """设置Agent使用的Provider"""
        if provider_name in self.providers:
            self.agent_provider[agent_name] = provider_name
            self._save_config()
    
    def set_agent_model(self, agent_name: str, model: str):
        """设置Agent使用的模型"""
        self.agent_model[agent_name] = model
        self._save_config()
    
    def _save_config(self):
        """保存配置到环境变量和文件"""
        # 保存到环境变量
        for agent, provider in self.agent_provider.items():
            env_key = f'{agent.upper()}_PROVIDER'
            os.environ[env_key] = provider
        
        for agent, model in self.agent_model.items():
            env_key = f'{agent.upper()}_MODEL'
            os.environ[env_key] = model
        
        # 保存到.env文件
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', '..', '.env')
        config_lines = []
        
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                config_lines = f.readlines()
        
        # 更新或添加配置
        new_lines = []
        for line in config_lines:
            skip = False
            for agent in ['HPUAssistant', 'StateEvaluator', 'ExerciseCoach', 'NutritionPlanner', 'GuardrailAuditor']:
                if line.startswith(f'{agent.upper()}_PROVIDER=') or line.startswith(f'{agent.upper()}_MODEL='):
                    skip = True
                    break
            if not skip:
                new_lines.append(line)
        
        # 添加新配置
        for agent, provider in self.agent_provider.items():
            new_lines.append(f'{agent.upper()}_PROVIDER={provider}\n')
        for agent, model in self.agent_model.items():
            new_lines.append(f'{agent.upper()}_MODEL={model}\n')
        
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
    
    def get_agent_config(self) -> Dict[str, Any]:
        """获取所有Agent的配置"""
        result = {}
        for agent in ['HPUAssistant', 'StateEvaluator', 'ExerciseCoach', 'NutritionPlanner', 'GuardrailAuditor']:
            provider = self.get_provider_for_agent(agent)
            result[agent] = {
                'provider': self.agent_provider.get(agent),
                'model': self.agent_model.get(agent),
                'available_models': provider.get_models() if provider else [],
                'provider_available': bool(provider and provider.api_key)
            }
        return result


# 全局实例
ai_manager = AIManager()


def get_ai_manager() -> AIManager:
    """获取AI管理器实例"""
    return ai_manager
