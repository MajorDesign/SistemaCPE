-- =====================================================================
-- 061_chat_voice.sql
-- Canais de voz persistentes estilo Discord + sessoes ativas (quem
-- esta AGORA conectado na sala de voz).
--
-- chat_voice_sessions e transient — INSERT no join, DELETE no leave.
-- peer_id e gerado client-side (UUID) e identifica univocamente esta
-- conexao no signaling WebRTC.
-- =====================================================================

USE `cpe_chat`;

ALTER TABLE `chat_channels`
  MODIFY `tipo` ENUM('dm','grupo_sistema','canal','voz') NOT NULL;

CREATE TABLE IF NOT EXISTS `chat_voice_sessions` (
  `channel_id` BIGINT       NOT NULL,
  `user_id`    BIGINT       NOT NULL COMMENT 'soft ref cpe_plus.users.id',
  `peer_id`    VARCHAR(40)  NOT NULL COMMENT 'UUID gerado no client pra signaling',
  `entrou_em`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `mic_on`     TINYINT(1)   NOT NULL DEFAULT 1,
  `cam_on`     TINYINT(1)   NOT NULL DEFAULT 0,
  `share_on`   TINYINT(1)   NOT NULL DEFAULT 0,
  PRIMARY KEY (`channel_id`, `user_id`),
  INDEX `idx_voice_user`    (`user_id`),
  INDEX `idx_voice_peer`    (`peer_id`),
  CONSTRAINT `fk_voice_channel`
    FOREIGN KEY (`channel_id`) REFERENCES `chat_channels`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
