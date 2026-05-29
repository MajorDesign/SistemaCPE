-- =====================================================================
-- 058_chat_mentions_reactions.sql
-- Adiciona @mentions e reactions emoji no chat. Roda no `cpe_chat`.
-- =====================================================================

USE `cpe_chat`;

-- ---------------------------------------------------------------------
-- chat_mentions — quem foi mencionado em qual mensagem.
-- Usado pra: badge especial no canal de quem foi citado, view "minhas
-- mentions", e bypass do mute em notificacao push.
-- Mensagens armazenam mention como token `<@user_id>` no content; esta
-- tabela e um indice paralelo pra consulta rapida.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `chat_mentions` (
  `message_id` BIGINT   NOT NULL,
  `user_id`    BIGINT   NOT NULL COMMENT 'soft ref cpe_plus.users.id',
  `criado_em`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`message_id`, `user_id`),
  INDEX `idx_chat_mentions_user` (`user_id`, `criado_em`),
  CONSTRAINT `fk_chat_mentions_msg`
    FOREIGN KEY (`message_id`) REFERENCES `chat_messages`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- chat_message_reactions — emoji de reacao por user/msg.
-- PK composto (message_id, user_id, emoji) permite que o mesmo user
-- reaja com varios emojis diferentes mas nao duplique o mesmo.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `chat_message_reactions` (
  `message_id` BIGINT       NOT NULL,
  `user_id`    BIGINT       NOT NULL COMMENT 'soft ref cpe_plus.users.id',
  `emoji`      VARCHAR(16)  NOT NULL COMMENT 'emoji unicode (1-4 chars normalmente)',
  `criado_em`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`message_id`, `user_id`, `emoji`),
  INDEX `idx_chat_react_msg_emoji` (`message_id`, `emoji`),
  CONSTRAINT `fk_chat_react_msg`
    FOREIGN KEY (`message_id`) REFERENCES `chat_messages`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
