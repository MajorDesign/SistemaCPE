-- =====================================================================
-- 066_chat_roles.sql
-- Cargos (roles) por servidor estilo Discord:
--   - chat_roles                 : definicao do cargo (nome, cor, ordem, perms)
--   - chat_role_members          : N:N user x role (user pode ter varios cargos)
--   - chat_channel_role_access   : whitelist de cargos por canal
--
-- Regras de acesso (canal DE servidor — server_id != NULL):
--   - Owner do server VE TUDO (bypass).
--   - Se canal nao tem entrada em chat_channel_role_access -> todos os
--     membros do server veem.
--   - Se tem entrada -> so quem tem PELO MENOS UM dos cargos listados ve.
--
-- Canais SOLTOS (server_id IS NULL) seguem com chat_channel_members
-- (adesao manual) inalterado.
-- =====================================================================

USE `cpe_chat`;

CREATE TABLE IF NOT EXISTS `chat_roles` (
  `id`         BIGINT       NOT NULL AUTO_INCREMENT,
  `server_id`  BIGINT       NOT NULL,
  `nome`       VARCHAR(80)  NOT NULL,
  `cor`        VARCHAR(7)   NULL COMMENT 'Hex #RRGGBB; NULL = sem cor',
  `ordem`      INT          NOT NULL DEFAULT 0 COMMENT 'maior = hierarquia mais alta',
  -- Permissoes binarias (flags)
  `perm_manage_server`    TINYINT(1) NOT NULL DEFAULT 0,
  `perm_manage_roles`     TINYINT(1) NOT NULL DEFAULT 0,
  `perm_manage_channels`  TINYINT(1) NOT NULL DEFAULT 0,
  `perm_manage_members`   TINYINT(1) NOT NULL DEFAULT 0,
  `perm_manage_messages`  TINYINT(1) NOT NULL DEFAULT 0,
  `perm_create_invite`    TINYINT(1) NOT NULL DEFAULT 1,
  `perm_mention_everyone` TINYINT(1) NOT NULL DEFAULT 0,
  `criado_por` BIGINT      NOT NULL COMMENT 'soft ref cpe_plus.users.id',
  `criado_em`  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_roles_server` (`server_id`, `ordem`),
  CONSTRAINT `fk_roles_server`
    FOREIGN KEY (`server_id`) REFERENCES `chat_servers`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `chat_role_members` (
  `role_id`       BIGINT   NOT NULL,
  `user_id`       BIGINT   NOT NULL COMMENT 'soft ref cpe_plus.users.id',
  `atribuido_em`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`role_id`, `user_id`),
  INDEX `idx_role_members_user` (`user_id`),
  CONSTRAINT `fk_role_members_role`
    FOREIGN KEY (`role_id`) REFERENCES `chat_roles`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `chat_channel_role_access` (
  `channel_id` BIGINT   NOT NULL,
  `role_id`    BIGINT   NOT NULL,
  `criado_em`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`channel_id`, `role_id`),
  INDEX `idx_channel_role_role` (`role_id`),
  CONSTRAINT `fk_channel_role_channel`
    FOREIGN KEY (`channel_id`) REFERENCES `chat_channels`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_channel_role_role`
    FOREIGN KEY (`role_id`) REFERENCES `chat_roles`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
