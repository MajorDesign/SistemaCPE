-- =====================================================================
-- Migration 023 — Pré-cadastro de usuários (auto-cadastro guiado)
--
-- Adiciona o fluxo de "Primeiro acesso" na tela de login:
--   1) Admin importa CSV de e-mails autorizados (exportados do Carbonio)
--   2) Usuário entra na tela de login, clica "Primeiro acesso", informa
--      o e-mail; se autorizado, preenche nome+senha e escolhe um grupo
--   3) Solicitação fica pendente até admin aprovar/recusar
--
-- Tabelas:
--   pre_cadastro_emails     -> lista de e-mails liberados (importados)
--   pre_cadastro_pendentes  -> solicitações de cadastro aguardando aprovação
--
-- Coluna nova:
--   cpe_grupo.visivel_signup -> controla se o grupo aparece no auto-cadastro
-- =====================================================================

-- =====================================================================
-- 1) Lista de e-mails autorizados (CSV importado pelo admin)
-- =====================================================================
CREATE TABLE IF NOT EXISTS `pre_cadastro_emails` (
  `id`             INT             NOT NULL AUTO_INCREMENT,
  `email`          VARCHAR(190)    NOT NULL,
  `nome_sugerido`  VARCHAR(120)    DEFAULT NULL,
  `status`         ENUM('disponivel','usado') NOT NULL DEFAULT 'disponivel',
  `importado_em`   TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `importado_por`  BIGINT          DEFAULT NULL,
  `usado_em`       TIMESTAMP       NULL DEFAULT NULL,
  `user_id`        BIGINT          DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_email` (`email`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 2) Solicitações de cadastro pendentes de aprovação
-- =====================================================================
CREATE TABLE IF NOT EXISTS `pre_cadastro_pendentes` (
  `id`              INT             NOT NULL AUTO_INCREMENT,
  `email`           VARCHAR(190)    NOT NULL,
  `name`            VARCHAR(120)    NOT NULL,
  `username`        VARCHAR(50)     NOT NULL,
  `password_hash`   VARCHAR(255)    NOT NULL,
  `group_id`        INT             NOT NULL,
  `status`          ENUM('pendente','aprovado','recusado') NOT NULL DEFAULT 'pendente',
  `solicitado_em`   TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `respondido_por`  BIGINT          DEFAULT NULL,
  `respondido_em`   TIMESTAMP       NULL DEFAULT NULL,
  `motivo_recusa`   TEXT            DEFAULT NULL,
  `user_id`         BIGINT          DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_email` (`email`),
  KEY `idx_status` (`status`),
  KEY `idx_group` (`group_id`),
  CONSTRAINT `fk_precad_group` FOREIGN KEY (`group_id`)
      REFERENCES `cpe_grupo` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 3) Flag visivel_signup em cpe_grupo
--    Controla quais grupos aparecem na tela de auto-cadastro.
--    Por padrão TODOS aparecem (1). Grupos administrativos devem ser
--    marcados manualmente como 0.
-- =====================================================================
SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME   = 'cpe_grupo'
      AND COLUMN_NAME  = 'visivel_signup'
);
SET @sql := IF(@col_exists = 0,
    'ALTER TABLE `cpe_grupo` ADD COLUMN `visivel_signup` TINYINT(1) NOT NULL DEFAULT 1 AFTER `description`',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Esconde grupos com nome contendo "admin" (case-insensitive) por padrão.
-- Admin pode reverter na tela de groups.html.
UPDATE `cpe_grupo`
   SET `visivel_signup` = 0
 WHERE LOWER(`name`) LIKE '%admin%';
