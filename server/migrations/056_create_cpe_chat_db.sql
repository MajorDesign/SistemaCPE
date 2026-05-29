-- =====================================================================
-- 056_create_cpe_chat_db.sql
-- Cria database separado `cpe_chat` pro modulo de chat realtime (estilo
-- Discord). DB separado pra isolar backup/limpeza/scale do alto volume
-- de mensagens. Mesma instancia MariaDB (sem custo de outro server).
--
-- Cross-database FK nao e suportado em MySQL/MariaDB, entao user_id e
-- grupo_id sao "soft refs" pra cpe_plus.users.id e cpe_plus.cpe_grupo.id
-- (referencia logica, sem constraint fisica).
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `cpe_chat`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `cpe_chat`;

-- ---------------------------------------------------------------------
-- chat_channels — DMs, canais por grupo do sistema, canais customizados
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `chat_channels` (
  `id`            BIGINT       NOT NULL AUTO_INCREMENT,
  `tipo`          ENUM('dm','grupo_sistema','canal') NOT NULL,
  `nome`          VARCHAR(100) NULL COMMENT 'NULL em DMs (deriva de membros)',
  `descricao`     VARCHAR(255) NULL,
  `grupo_id`      INT          NULL COMMENT 'soft ref cpe_plus.cpe_grupo.id (para canais automaticos por grupo)',
  `criado_por`    BIGINT       NULL COMMENT 'soft ref cpe_plus.users.id',
  `criado_em`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `arquivado_em`  DATETIME     NULL,
  PRIMARY KEY (`id`),
  INDEX `idx_chat_channels_tipo`  (`tipo`),
  INDEX `idx_chat_channels_grupo` (`grupo_id`),
  UNIQUE KEY `uk_chat_channels_grupo` (`grupo_id`)
    COMMENT 'Garante 1 canal automatico por grupo do sistema'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- chat_channel_members — quem pertence a cada canal
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `chat_channel_members` (
  `channel_id`           BIGINT   NOT NULL,
  `user_id`              BIGINT   NOT NULL COMMENT 'soft ref cpe_plus.users.id',
  `role`                 ENUM('owner','admin','member') NOT NULL DEFAULT 'member',
  `entrou_em`            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `silenciado_ate`       DATETIME NULL,
  `ultima_msg_lida_id`   BIGINT   NULL COMMENT 'soft ref chat_messages.id',
  PRIMARY KEY (`channel_id`, `user_id`),
  INDEX `idx_chat_members_user` (`user_id`),
  CONSTRAINT `fk_chat_members_channel`
    FOREIGN KEY (`channel_id`) REFERENCES `chat_channels`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- chat_messages — mensagens (alto-volume, indices criticos)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `chat_messages` (
  `id`           BIGINT    NOT NULL AUTO_INCREMENT,
  `channel_id`   BIGINT    NOT NULL,
  `user_id`      BIGINT    NOT NULL COMMENT 'soft ref cpe_plus.users.id (autor)',
  `content`      TEXT      NOT NULL,
  `reply_to_id`  BIGINT    NULL COMMENT 'soft ref chat_messages.id (resposta)',
  `criado_em`    DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `editado_em`   DATETIME  NULL,
  `deletado_em`  DATETIME  NULL COMMENT 'soft delete pra preservar continuidade',
  PRIMARY KEY (`id`),
  INDEX `idx_chat_msgs_channel_time` (`channel_id`, `criado_em`)
    COMMENT 'historico paginado por canal',
  INDEX `idx_chat_msgs_user` (`user_id`),
  CONSTRAINT `fk_chat_msgs_channel`
    FOREIGN KEY (`channel_id`) REFERENCES `chat_channels`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- chat_presence — status online/offline pra UI (lista de membros)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `chat_presence` (
  `user_id`           BIGINT   NOT NULL COMMENT 'soft ref cpe_plus.users.id',
  `status`            ENUM('online','idle','offline') NOT NULL DEFAULT 'offline',
  `ultima_atividade`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
