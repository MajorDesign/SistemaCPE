-- =====================================================================
-- Migration 038 — Numero de serie + dedup de vinculo em inventario_itens
--
-- 1) Adiciona `numero_serie` para registrar a serie de hardware
--    (auto-preenchido do agente quando vinculado a um dispositivo).
--
-- 2) Indice UNIQUE em `dispositivo_id` para garantir, no nivel do banco,
--    que cada equipamento monitorado tenha NO MAXIMO um item financeiro
--    vinculado. NULL pode repetir (itens avulsos sem vinculo continuam OK).
--
-- Idempotente.
-- =====================================================================

-- numero_serie
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'inventario_itens'
    AND COLUMN_NAME  = 'numero_serie'
);
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE `inventario_itens` ADD COLUMN `numero_serie` VARCHAR(150) DEFAULT NULL COMMENT ''Serial number do hardware (auto-preenchido se vinculado a agente)'' AFTER `codigo`',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Indice por numero_serie (busca, sem unique pra permitir series vazias)
SET @idx_exists := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'inventario_itens'
    AND INDEX_NAME   = 'idx_numero_serie'
);
SET @sql := IF(@idx_exists = 0,
  'ALTER TABLE `inventario_itens` ADD INDEX `idx_numero_serie` (`numero_serie`)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- UNIQUE em dispositivo_id (so 1 item financeiro por equipamento monitorado).
-- MySQL/MariaDB permitem multiplos NULLs em coluna UNIQUE, entao itens
-- avulsos (sem dispositivo) nao colidem.
-- Antes de criar, REMOVE o indice nao-unique antigo se existir.
SET @old_idx := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'inventario_itens'
    AND INDEX_NAME   = 'idx_dispositivo'
    AND NON_UNIQUE   = 1
);
SET @sql := IF(@old_idx > 0,
  'ALTER TABLE `inventario_itens` DROP INDEX `idx_dispositivo`',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @uniq_exists := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'inventario_itens'
    AND INDEX_NAME   = 'uk_dispositivo_id'
);
SET @sql := IF(@uniq_exists = 0,
  'ALTER TABLE `inventario_itens` ADD UNIQUE KEY `uk_dispositivo_id` (`dispositivo_id`)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
