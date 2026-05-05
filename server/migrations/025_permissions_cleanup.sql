-- =====================================================================
-- Migration 025 — Limpeza pós-refatoração de permissões
--
-- Renomeia `page_permissions` (modelo CSV antigo) para
-- `_legacy_page_permissions`. Os dados foram migrados na Fase 1
-- pelo permission_migrator.py para as tabelas relacionais
-- (permission_pages + permission_page_role).
--
-- Mantemos a legacy renomeada (não DROP) por segurança — caso
-- surja algum problema, basta:
--     RENAME TABLE _legacy_page_permissions TO page_permissions;
-- =====================================================================

-- Idempotente: só renomeia se a tabela velha ainda existe
SET @existe := (
  SELECT COUNT(*) FROM information_schema.TABLES
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'page_permissions'
);
SET @ja_legacy := (
  SELECT COUNT(*) FROM information_schema.TABLES
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '_legacy_page_permissions'
);

SET @sql := IF(@existe = 1 AND @ja_legacy = 0,
    'RENAME TABLE `page_permissions` TO `_legacy_page_permissions`',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
