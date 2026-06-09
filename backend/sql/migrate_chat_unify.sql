-- ================================================
-- 迁移：统一会话历史到 ai_conversations + 补齐演示所需列
-- 执行：psql -U postgres -d hpu_db -f migrate_chat_unify.sql
-- 说明：全部为幂等语句，重复执行安全。后端代码首次写入时也会自动执行同样的 DDL，
--      因此本脚本主要用于显式留痕 / 手动初始化。
-- ================================================

-- 1. users 增补体脂率列（设计方案 §8.4 身体测量需要，库内原缺）
ALTER TABLE users ADD COLUMN IF NOT EXISTS body_fat_pct FLOAT;

-- 2. ai_conversations 以 session_id 作为会话键，需唯一索引以支持按会话 UPSERT
CREATE UNIQUE INDEX IF NOT EXISTS uq_ai_conv_session ON ai_conversations(session_id);

-- 3.（可选）将旧的 chat_conversations 历史迁移到 ai_conversations，归属演示用户 id=1
--    仅迁移 chat_conversations 表存在时执行；不存在则跳过。
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'chat_conversations') THEN
        INSERT INTO ai_conversations (user_id, session_id, messages, created_at)
        SELECT 1, conversation_id, messages, created_at
        FROM chat_conversations
        ON CONFLICT (session_id) DO NOTHING;
        RAISE NOTICE '已尝试迁移 chat_conversations -> ai_conversations';
    END IF;
END $$;

-- 4.（可选，确认迁移无误后再手动执行）废弃旧表：
-- DROP TABLE IF EXISTS chat_conversations;

-- ================================================
-- 完成
-- ================================================
