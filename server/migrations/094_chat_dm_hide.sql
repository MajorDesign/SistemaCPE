-- =========================================================
-- 094_chat_dm_hide.sql — DM arquivada por user (soft-hide)
-- =========================================================
-- DB: cpe_chat
--
-- Permite que um user "arquive" uma DM sem apagar pra todo mundo.
-- - user X arquiva DM com Y -> canal some da sidebar do X.
-- - Y continua vendo normal.
-- - Se X mandar uma mensagem nova ou reabrir a conversa pelo botao
--   "Nova conversa", o backend limpa `ocultado_em` (auto-unhide).
--
-- Aditiva; nao altera dados.

USE cpe_chat;

ALTER TABLE chat_channel_members
  ADD COLUMN ocultado_em DATETIME NULL AFTER silenciado_ate;

CREATE INDEX idx_ccm_ocultado
  ON chat_channel_members (user_id, ocultado_em);
