-- =====================================================================
-- 064_chat_invites.sql
-- Links de convite pra servidores e canais (estilo Discord).
--
-- - code: identificador curto (8 chars alfanumericos) usado na URL
--         pra entrar via /SistemaCPE/web/pages/chat.html?invite=ABC123
-- - server_id: sempre setado (todo invite leva pra dentro de um server)
-- - channel_id: opcional — se setado, accept tambem adiciona ao canal
-- - expira_em: NULL = nunca expira
-- - max_usos: NULL = ilimitado
-- - revogado_em: soft-delete; criador ou owner/admin do server podem revogar
--
-- Qualquer membro do server pode criar invite (regra simples; restringir
-- depois se necessario).
-- =====================================================================

USE `cpe_chat`;

CREATE TABLE IF NOT EXISTS `chat_invites` (
  `id`           BIGINT       NOT NULL AUTO_INCREMENT,
  `code`         VARCHAR(16)  NOT NULL,
  `server_id`    BIGINT       NOT NULL,
  `channel_id`   BIGINT       NULL,
  `criado_por`   BIGINT       NOT NULL COMMENT 'soft ref cpe_plus.users.id',
  `criado_em`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `expira_em`    DATETIME     NULL,
  `max_usos`     INT          NULL COMMENT 'NULL = ilimitado',
  `usos`         INT          NOT NULL DEFAULT 0,
  `revogado_em`  DATETIME     NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_invites_code` (`code`),
  INDEX `idx_invites_server` (`server_id`),
  INDEX `idx_invites_channel` (`channel_id`),
  CONSTRAINT `fk_invites_server`
    FOREIGN KEY (`server_id`)  REFERENCES `chat_servers`(`id`)  ON DELETE CASCADE,
  CONSTRAINT `fk_invites_channel`
    FOREIGN KEY (`channel_id`) REFERENCES `chat_channels`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
