-- =====================================================================
-- 059_chat_pinned.sql
-- Pin de mensagem importante no canal. Coluna pinned_at em chat_messages
-- (NULL = nao fixada). Pra um canal ter "mensagens fixadas", o frontend
-- busca WHERE channel_id=X AND pinned_at IS NOT NULL.
--
-- Decisao: coluna em vez de tabela separada porque busca pinada por
-- canal e simples (WHERE c.id=X AND m.pinned_at IS NOT NULL ORDER BY
-- m.pinned_at DESC LIMIT 50) e nao precisa de JOIN extra.
--
-- Tambem cria indice FULLTEXT em content pra busca de mensagens.
-- =====================================================================

USE `cpe_chat`;

ALTER TABLE `chat_messages`
  ADD COLUMN `pinned_at` DATETIME NULL DEFAULT NULL
    COMMENT 'NULL = nao fixada; senao quando foi fixada'
  AFTER `deletado_em`;

CREATE INDEX `idx_chat_msgs_pinned`
  ON `chat_messages` (`channel_id`, `pinned_at`);

-- Indice fulltext pra busca de texto em mensagens
ALTER TABLE `chat_messages`
  ADD FULLTEXT INDEX `ftx_chat_msgs_content` (`content`);
