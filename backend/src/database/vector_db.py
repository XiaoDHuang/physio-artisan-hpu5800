"""
向量数据库模块 - 用于AI Embedding存储和检索

使用场景:
1. 训练计划相似推荐
2. 饮食方案相似推荐
3. 用户行为序列分析
4. 智能问答增强
"""

import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass


# =============================================================================
# 向量数据模型
# =============================================================================

@dataclass
class EmbeddingRecord:
    """向量记录"""
    id: Optional[int]
    user_id: int
    content_type: str  # 'exercise', 'food', 'chat', 'training_plan'
    content: str
    embedding: List[float]
    metadata: Dict  # 存储额外信息
    created_at: datetime
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "content_type": self.content_type,
            "content": self.content,
            "embedding": self.embedding,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class VectorDB:
    """
    向量数据库管理器
    
    功能:
    1. 存储Embedding
    2. 相似度检索
    3. 过滤查询
    
    支持后端:
    - GaussDB内置向量检索
    - Milvus
    - Qdrant
    - 内存模拟 (开发测试)
    """
    
    def __init__(self, backend: str = "memory"):
        """
        初始化向量库
        
        Args:
            backend: 'gaussdb', 'milvus', 'qdrant', 'memory'
        """
        self.backend = backend
        self.embeddings: List[EmbeddingRecord] = []  # 内存存储(开发用)
        self._initialized = False
    
    def init(self):
        """初始化向量库"""
        if self._initialized:
            return
        
        if self.backend == "gaussdb":
            self._init_gaussdb()
        elif self.backend == "milvus":
            self._init_milvus()
        elif self.backend == "memory":
            self._init_memory()
        
        self._initialized = True
    
    def _init_memory(self):
        """初始化内存存储"""
        print("向量库: 内存模式 (开发测试)")
    
    def _init_gaussdb(self):
        """初始化GaussDB向量检索"""
        print("向量库: GaussDB向量检索")
        # 真实实现需要连接GaussDB
        # CREATE EXTENSION IF NOT EXISTS vector;
        # CREATE TABLE embeddings (... embedding vector(1536));
    
    def _init_milvus(self):
        """初始化Milvus"""
        print("向量库: Milvus")
    
    # =============================================================================
    # Embedding 生成 (需要调用LLM API)
    # =============================================================================
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        生成文本Embedding
        
        使用OpenAI或其他Embedding模型
        默认返回随机向量(开发测试用)
        """
        import hashlib
        import numpy as np
        
        # 模拟Embedding (真实项目使用OpenAI API)
        # response = openai.Embedding.create(
        #     model="text-embedding-ada-002",
        #     input=text
        # )
        # return response['data'][0]['embedding']
        
        # 开发测试：用文本hash生成确定性随机向量
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        np.random.seed(hash_val % (2**32))
        return np.random.randn(1536).tolist()  # OpenAI ada-002维度
    
    # =============================================================================
    # CRUD 操作
    # =============================================================================
    
    def add(
        self,
        user_id: int,
        content_type: str,
        content: str,
        metadata: Dict = None,
        embedding: List[float] = None
    ) -> int:
        """
        添加向量记录
        
        Returns:
            record_id
        """
        if not self._initialized:
            self.init()
        
        # 生成Embedding
        if embedding is None:
            embedding = self.generate_embedding(content)
        
        record = EmbeddingRecord(
            id=len(self.embeddings) + 1,
            user_id=user_id,
            content_type=content_type,
            content=content,
            embedding=embedding,
            metadata=metadata or {},
            created_at=datetime.now()
        )
        
        self.embeddings.append(record)
        return record.id
    
    def search(
        self,
        query: str,
        user_id: Optional[int] = None,
        content_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Tuple[EmbeddingRecord, float]]:
        """
        相似度搜索
        
        Args:
            query: 查询文本
            user_id: 用户ID过滤
            content_type: 内容类型过滤
            top_k: 返回数量
            
        Returns:
            [(record, similarity_score), ...]
        """
        if not self._initialized:
            self.init()
        
        # 生成查询向量
        query_embedding = self.generate_embedding(query)
        
        # 过滤
        candidates = self.embeddings
        
        if user_id is not None:
            candidates = [r for r in candidates if r.user_id == user_id]
        
        if content_type is not None:
            candidates = [r for r in candidates if r.content_type == content_type]
        
        # 计算相似度
        results = []
        for record in candidates:
            similarity = self._cosine_similarity(query_embedding, record.embedding)
            results.append((record, similarity))
        
        # 排序返回top_k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        import math
        
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def delete(self, record_id: int) -> bool:
        """删除记录"""
        for i, record in enumerate(self.embeddings):
            if record.id == record_id:
                del self.embeddings[i]
                return True
        return False
    
    def get_by_user(self, user_id: int, content_type: str = None) -> List[EmbeddingRecord]:
        """获取用户的所有记录"""
        results = [r for r in self.embeddings if r.user_id == user_id]
        if content_type:
            results = [r for r in results if r.content_type == content_type]
        return results


# =============================================================================
# HPU特定用例
# =============================================================================

class HPURecommender:
    """
    HPU推荐系统
    基于向量数据库的智能推荐
    """
    
    def __init__(self):
        self.vector_db = VectorDB(backend="memory")
        self.vector_db.init()
    
    def index_training_plan(self, user_id: int, plan: Dict):
        """索引训练计划"""
        plan_text = self._serialize_training_plan(plan)
        self.vector_db.add(
            user_id=user_id,
            content_type="training_plan",
            content=plan_text,
            metadata={
                "plan_id": plan.get("id"),
                "focus": plan.get("focus"),
                "duration": plan.get("duration"),
                "calories": plan.get("estimated_calories")
            }
        )
    
    def recommend_similar_plans(
        self,
        user_id: int,
        current_plan: Dict,
        top_k: int = 3
    ) -> List[Dict]:
        """
        推荐相似的训练计划
        
        用于:
        - 历史计划复用
        - 相似用户计划推荐
        """
        query = self._serialize_training_plan(current_plan)
        results = self.vector_db.search(
            query=query,
            user_id=user_id,
            content_type="training_plan",
            top_k=top_k
        )
        
        return [
            {
                "plan": result[0].metadata,
                "similarity": round(result[1], 3),
                "content": result[0].content
            }
            for result in results
        ]
    
    def index_food(self, user_id: int, food_data: Dict):
        """索引食物记录"""
        food_text = f"{food_data['name']}: {food_data.get('calories', 0)}卡路里"
        self.vector_db.add(
            user_id=user_id,
            content_type="food",
            content=food_text,
            metadata={
                "calories": food_data.get("calories"),
                "protein": food_data.get("protein"),
                "carbs": food_data.get("carbs"),
                "fat": food_data.get("fat")
            }
        )
    
    def recommend_foods(
        self,
        user_id: int,
        target_calories: int,
        top_k: int = 5
    ) -> List[Dict]:
        """推荐相似的食物"""
        query = f"低热量食物 {target_calories}卡路里"
        results = self.vector_db.search(
            query=query,
            user_id=user_id,
            content_type="food",
            top_k=top_k
        )
        
        return [
            {
                "food": result[0].metadata,
                "similarity": round(result[1], 3)
            }
            for result in results
        ]
    
    def _serialize_training_plan(self, plan: Dict) -> str:
        """序列化训练计划为文本"""
        parts = [
            f"训练类型: {plan.get('focus', '综合')}",
            f"训练强度: {plan.get('intensity', '中等')}",
            f"预计时长: {plan.get('duration', 60)}分钟",
            f"预计消耗: {plan.get('estimated_calories', 300)}卡路里"
        ]
        
        if "exercises" in plan:
            exercises = ", ".join([e.get("name", "") for e in plan["exercises"][:5]])
            parts.append(f"动作: {exercises}")
        
        return " | ".join(parts)


# =============================================================================
# 使用示例
# =============================================================================

def demo():
    """演示向量数据库功能"""
    
    print("=" * 50)
    print("HPU 向量数据库演示")
    print("=" * 50)
    
    # 初始化
    recommender = HPURecommender()
    
    # 1. 索引一些训练计划
    print("\n📝 索引训练计划...")
    
    plans = [
        {
            "id": 1,
            "focus": "减脂",
            "intensity": "高",
            "duration": 45,
            "estimated_calories": 400,
            "exercises": [
                {"name": "深蹲", "sets": 4},
                {"name": "波比跳", "sets": 3}
            ]
        },
        {
            "id": 2,
            "focus": "增肌",
            "intensity": "中高",
            "duration": 60,
            "estimated_calories": 350,
            "exercises": [
                {"name": "卧推", "sets": 5},
                {"name": "划船", "sets": 4}
            ]
        },
        {
            "id": 3,
            "focus": "体能",
            "intensity": "高",
            "duration": 30,
            "estimated_calories": 300,
            "exercises": [
                {"name": "HIIT", "sets": 10}
            ]
        }
    ]
    
    for plan in plans:
        recommender.index_training_plan(user_id=1, plan=plan)
        print(f"  ✅ 已索引: {plan['focus']}训练")
    
    # 2. 搜索相似计划
    print("\n🔍 搜索相似训练计划...")
    
    query_plan = {
        "focus": "减脂",
        "intensity": "高",
        "duration": 40,
        "estimated_calories": 380
    }
    
    similar = recommender.recommend_similar_plans(
        user_id=1,
        current_plan=query_plan,
        top_k=3
    )
    
    for i, rec in enumerate(similar, 1):
        print(f"\n  推荐 {i}:")
        print(f"    相似度: {rec['similarity']}")
        print(f"    内容: {rec['content']}")
    
    # 3. 索引食物
    print("\n🍽️ 索引食物数据...")
    
    foods = [
        {"name": "鸡胸肉", "calories": 133, "protein": 31, "carbs": 0, "fat": 1.2},
        {"name": "西兰花", "calories": 34, "protein": 2.8, "carbs": 6.6, "fat": 0.4},
        {"name": "米饭", "calories": 130, "protein": 2.7, "carbs": 28, "fat": 0.3}
    ]
    
    for food in foods:
        recommender.index_food(user_id=1, food_data=food)
        print(f"  ✅ 已索引: {food['name']}")
    
    # 4. 推荐食物
    print("\n🍽️ 推荐食物...")
    
    recommended = recommender.recommend_foods(
        user_id=1,
        target_calories=100,
        top_k=3
    )
    
    for rec in recommended:
        food = rec['food']
        print(f"  推荐: {food.get('name', '未知')} - {food.get('calories', 0)}卡")
    
    print("\n" + "=" * 50)
    print("演示完成!")
    print("=" * 50)


if __name__ == "__main__":
    demo()
