-- =====================================================================
-- 057_chat_attachments.sql
-- Tabela de anexos das mensagens do chat (atualmente: imagens; futuro:
-- documentos, audio, video). Roda no database `cpe_chat`.
--
-- Politica: imagens sao deletadas do disco apos 90 dias (cleanup chamado
-- por endpoint admin OU job agendado). Linha do DB tambem e removida.
-- =====================================================================

USE `cpe_chat`;

CREATE TABLE IF NOT EXISTS `chat_attachments` (
  `id`           BIGINT       NOT NULL AUTO_INCREMENT,
  `message_id`   BIGINT       NOT NULL,
  `tipo`         ENUM('image') NOT NULL DEFAULT 'image',
  `arquivo`      VARCHAR(255) NOT NULL COMMENT 'caminho URL relativo ao web/uploads/chat/',
  `nome_original` VARCHAR(255) NULL,
  `mime`         VARCHAR(80)  NULL,
  `tamanho`      BIGINT       NULL COMMENT 'bytes',
  `criado_em`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_chat_att_msg`  (`message_id`),
  INDEX `idx_chat_att_data` (`criado_em`) COMMENT 'usado pelo cleanup',
  CONSTRAINT `fk_chat_att_msg`
    FOREIGN KEY (`message_id`) REFERENCES `chat_messages`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
