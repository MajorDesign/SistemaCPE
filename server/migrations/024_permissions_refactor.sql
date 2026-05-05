-- =====================================================================
-- Migration 024 — Refatoração do sistema de permissões
--
-- Substitui o modelo "page_name + allowed_roles CSV" por um modelo
-- relacional limpo com 3 tabelas:
--
--   permission_pages         -> catálogo único de páginas
--   permission_page_role     -> M:N página↔role (substitui CSV)
--   permission_page_group    -> M:N página↔grupo (NOVA — controle por grupo)
--
-- A tabela velha `page_permissions` NÃO é apagada — ela só é renomeada
-- na FASE 4. Aqui apenas criamos as novas e copiaremos os dados via
-- código Python (permission_migrator.py).
--
-- Idempotente: pode rodar múltiplas vezes sem erro.
-- =====================================================================

-- =====================================================================
-- 1) CATÁLOGO DE PÁGINAS
--    Fonte da verdade. Populada pelo seeder Python no startup do app.
-- =====================================================================
CREATE TABLE IF NOT EXISTS `permission_pages` (
  `page_key`     VARCHAR(50)   NOT NULL,
  `display_name` VARCHAR(100)  NOT NULL,
  `description`  VARCHAR(255)  DEFAULT NULL,
  `category`     VARCHAR(20)   NOT NULL DEFAULT 'operational',
  `icon`         VARCHAR(50)   NOT NULL DEFAULT 'bi-file-earmark',
  `url`          VARCHAR(150)  DEFAULT NULL,
  `ordem`        INT           NOT NULL DEFAULT 100,
  `is_active`    TINYINT(1)    NOT NULL DEFAULT 1,
  `created_at`   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`page_key`),
  KEY `idx_category` (`category`),
  KEY `idx_ordem` (`ordem`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 2) ROLES PERMITIDOS POR PÁGINA (M:N)
-- =====================================================================
CREATE TABLE IF NOT EXISTS `permission_page_role` (
  `page_key` VARCHAR(50) NOT NULL,
  `role`     ENUM('USER','RESPONSAVEL_GRUPO','TI','MANAGER','ADMIN') NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`page_key`, `role`),
  CONSTRAINT `fk_ppr_page` FOREIGN KEY (`page_key`)
      REFERENCES `permission_pages` (`page_key`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 3) GRUPOS PERMITIDOS POR PÁGINA (M:N) — feature nova
-- =====================================================================
CREATE TABLE IF NOT EXISTS `permission_page_group` (
  `page_key`   VARCHAR(50) NOT NULL,
  `group_id`   INT         NOT NULL,
  `created_at` TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`page_key`, `group_id`),
  KEY `idx_group` (`group_id`),
  CONSTRAINT `fk_ppg_page`  FOREIGN KEY (`page_key`)
      REFERENCES `permission_pages` (`page_key`) ON DELETE CASCADE,
  CONSTRAINT `fk_ppg_group` FOREIGN KEY (`group_id`)
      REFERENCES `cpe_grupo` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- A tabela legada `page_permissions` permanece intacta neste momento.
-- Será renomeada para `_legacy_page_permissions` na FASE 4 da refatoração,
-- após validação completa do novo sistema.
-- =====================================================================
