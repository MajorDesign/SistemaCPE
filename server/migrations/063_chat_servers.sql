-- =====================================================================
-- 063_chat_servers.sql
-- Adiciona hierarquia estilo Discord: Servidor -> Categoria -> Canal.
--
-- - chat_servers           : workspace logico (ex: "CPE", "Suporte Externo")
-- - chat_server_members    : quem participa de cada servidor + role
-- - chat_categories        : agrupamento visual dentro do servidor
-- - chat_channels.server_id, categoria_id, ordem : posicionamento na arvore
--
-- Canais "soltos" (DMs, grupos do sistema, canais antigos) ficam com
-- server_id=NULL e seguem aparecendo na sidebar como hoje.
--
-- Adesao manual: virar membro do servidor NAO entra em todos os canais
-- automaticamente — entra via chat_channel_members existente quando o
-- admin convida ou o usuario aceita.
-- =====================================================================

USE `cpe_chat`;

-- ---------------------------------------------------------------------
-- chat_servers — workspace de canais (1 servidor = "Canal CPE")
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `chat_servers` (
  `id`           BIGINT       NOT NULL AUTO_INCREMENT,
  `nome`         VARCHAR(100) NOT NULL,
  `descricao`    VARCHAR(255) NULL,
  `icone`        VARCHAR(255) NULL COMMENT 'emoji ou URL de avatar do servidor',
  `criado_por`   BIGINT       NOT NULL COMMENT 'soft ref cpe_plus.users.id',
  `criado_em`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `arquivado_em` DATETIME     NULL,
  PRIMARY KEY (`id`),
  INDEX `idx_chat_servers_arquivado` (`arquivado_em`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- chat_server_members — membros + role no servidor
-- owner pode promover admins; admins criam categorias/canais e gerenciam membros.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `chat_server_members` (
  `server_id`  BIGINT   NOT NULL,
  `user_id`    BIGINT   NOT NULL COMMENT 'soft ref cpe_plus.users.id',
  `role`       ENUM('owner','admin','member') NOT NULL DEFAULT 'member',
  `entrou_em`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`server_id`, `user_id`),
  INDEX `idx_chat_server_members_user` (`user_id`),
  CONSTRAINT `fk_chat_server_members_server`
    FOREIGN KEY (`server_id`) REFERENCES `chat_servers`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- chat_categories — agrupamento visual dentro do servidor (opcional)
-- Canais com categoria_id=NULL ficam soltos no topo do servidor.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `chat_categories` (
  `id`         BIGINT       NOT NULL AUTO_INCREMENT,
  `server_id`  BIGINT       NOT NULL,
  `nome`       VARCHAR(100) NOT NULL,
  `ordem`      INT          NOT NULL DEFAULT 0,
  `criado_por` BIGINT       NOT NULL COMMENT 'soft ref cpe_plus.users.id',
  `criado_em`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_chat_categories_server` (`server_id`, `ordem`),
  CONSTRAINT `fk_chat_categories_server`
    FOREIGN KEY (`server_id`) REFERENCES `chat_servers`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- chat_channels — adiciona server_id + categoria_id + ordem
-- Mantem retro-compatibilidade: canais existentes ficam com server_id=NULL.
-- ---------------------------------------------------------------------
ALTER TABLE `chat_channels`
  ADD COLUMN `server_id`    BIGINT NULL AFTER `tipo`,
  ADD COLUMN `categoria_id` BIGINT NULL AFTER `server_id`,
  ADD COLUMN `ordem`        INT NOT NULL DEFAULT 0 AFTER `categoria_id`,
  ADD INDEX `idx_chat_channels_server`    (`server_id`, `ordem`),
  ADD INDEX `idx_chat_channels_categoria` (`categoria_id`, `ordem`);

-- SET NULL no delete pra preservar canais se a categoria for excluida
-- (eles voltam pra "raiz" do servidor).
ALTER TABLE `chat_channels`
  ADD CONSTRAINT `fk_chat_channels_server`
    FOREIGN KEY (`server_id`) REFERENCES `chat_servers`(`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_chat_channels_categoria`
    FOREIGN KEY (`categoria_id`) REFERENCES `chat_categories`(`id`) ON DELETE SET NULL;
