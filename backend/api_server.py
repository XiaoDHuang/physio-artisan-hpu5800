#!/usr/bin/env python3
"""
健身训练助手 - FastAPI 后端服务

仅提供一个 /chat 接口，基于大模型进行对话，支持 SSE 流式输出。
"""

import sys
import os
import json
import uuid
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.langgraph_config import langgraph_config as config
from store import get_store


# --------------------------- 日志配置 ---------------------------
def setup_api_logger():
    logger = logging.getLogger('api_server')
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        fh = logging.FileHandler('logs/backend.log', encoding='utf-8')
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    return logger


api_logger = setup_api_logger()

# --------------------------- 应用初始化 ---------------------------
app = FastAPI(
    title="健身训练助手",
    description="🤖 健身训练助手：您的智能健身助手",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = "你是\"健身训练助手\"，一个专业的AI健身训练助手，请用简洁友好的中文回答用户的健身相关问题。"


# --------------------------- 数据模型 ---------------------------
class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色：user（用户）/ assistant（助手）/ system（系统）", examples=["user"])
    content: str = Field(..., description="消息内容", examples=["帮我制定一个减脂训练计划"])


class ChatRequest(BaseModel):
    message: str = Field(..., description="用户本次发送的消息内容", examples=["帮我制定一个减脂训练计划"])
    conversation_id: Optional[str] = Field(
        default=None,
        description="会话ID。为空表示新建会话，历史由服务端维护；响应的首个 SSE 事件会返回本次使用的 conversation_id，前端请保存并在后续请求中带上以延续多轮对话。",
        examples=["a1b2c3d4e5f6"],
    )


class ConversationResponse(BaseModel):
    conversation_id: str = Field(..., description="会话ID")
    messages: List[ChatMessage] = Field(..., description="该会话的历史消息列表")


class ConversationSummaryItem(BaseModel):
    conversation_id: str = Field(..., description="会话ID")
    title: str = Field(..., description="会话标题（取首条用户消息）")
    updated_at: float = Field(..., description="最近更新时间（Unix 时间戳，秒）")


# --------------------------- 聊天接口（SSE 流式） ---------------------------
@app.post("/chat")
async def chat_with_ai(request: ChatRequest):
    """与大模型对话，使用 SSE 流式返回。

    历史记录由服务端按 conversation_id 维护：
    - 请求未带 conversation_id 时新建会话；
    - 首个 SSE 事件返回本次会话的 conversation_id；
    - 流式结束后，自动把本轮 user / assistant 消息写入会话历史。
    """
    conversation_id = request.conversation_id or uuid.uuid4().hex
    store = get_store()
    api_logger.info(f"收到聊天请求[会话 {conversation_id}]: {request.message}")

    # 从服务端取出该会话的历史，拼接为本次大模型输入
    history = await store.get_history(conversation_id)

    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=config.OPENAI_MODEL,
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_BASE_URL,
        temperature=0.7,
        streaming=True,
    )

    user_message = {"role": "user", "content": request.message}
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history, user_message]

    async def event_stream():
        # 先把会话ID发给前端，便于其保存并在后续请求中续接
        yield f"data: {json.dumps({'conversation_id': conversation_id}, ensure_ascii=False)}\n\n"

        chunks: List[str] = []
        try:
            async for chunk in llm.astream(messages):
                token = chunk.content
                if token:
                    chunks.append(token)
                    yield f"data: {json.dumps({'content': token}, ensure_ascii=False)}\n\n"
            # 流式成功结束后再持久化本轮对话，避免把失败的半截回复写入历史
            assistant_message = {"role": "assistant", "content": "".join(chunks)}
            await store.append(conversation_id, [user_message, assistant_message])
            yield "data: [DONE]\n\n"
        except Exception as e:
            api_logger.error(f"聊天流式输出失败[会话 {conversation_id}]: {e}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# --------------------------- 会话历史管理接口 ---------------------------
@app.get("/conversations", response_model=List[ConversationSummaryItem])
async def list_conversations():
    """列出所有会话摘要，按最近更新时间倒序（供前端历史栏拉取）。"""
    return await get_store().list_conversations()


@app.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str):
    """查询指定会话的历史消息。"""
    history = await get_store().get_history(conversation_id)
    return ConversationResponse(conversation_id=conversation_id, messages=history)


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """清空（删除）指定会话的历史。"""
    await get_store().clear(conversation_id)
    api_logger.info(f"已清空会话历史: {conversation_id}")
    return {"conversation_id": conversation_id, "status": "cleared"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
