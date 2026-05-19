-- =====================================================================
-- Migration 039 — Equipamento completo + justificativa de incompleto
--
-- Permite registrar se um equipamento esta completo ou se chegou faltando
-- pecas (memoria, HD, cabo, etc). Quando incompleto, exige justificativa.
--
-- Idempotente.
-- =====================================================================

-- completo (default 1 = completo)
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'inventario_itens'
    AND COLUMN_NAME  = 'completo'
);
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE `inventario_itens` ADD COLUMN `completo` TINYINT(1) NOT NULL DEFAULT 1 COMMENT ''0 = equipamento incompleto (falta peca)'' AFTER `descricao`',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- justificativa_incompleto
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'inventario_itens'
    AND COLUMN_NAME  = 'justificativa_incompleto'
);
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE `inventario_itens` ADD COLUMN `justificativa_incompleto` TEXT DEFAULT NULL COMMENT ''Motivo quando completo=0 (ex: faltou memoria)'' AFTER `completo`',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
