-- =====================================================================
-- Migration 035 — Estoque de equipamentos T.I. + dados de responsável
--
-- Adiciona à tabela `inventario_dispositivos` os campos necessários
-- para gerir equipamentos que foram recolhidos de colaboradores que
-- saíram da empresa (estoque para reutilização):
--
--   em_estoque        — 1 quando o equipamento está parado no estoque
--                       (não tem responsável ativo). Equipamentos em
--                       estoque continuam reportando via agente, mas
--                       são listados em aba separada da UI.
--   nome_responsavel  — nome do colaborador que usa o equipamento.
--   setor             — departamento do responsável.
--   localizacao_cpe   — unidade CPE onde o equipamento está fisicamente
--                       (BH, SP, etc). Preenchida pelo admin.
--
-- Idempotente: pode rodar múltiplas vezes sem erro.
-- =====================================================================

-- em_estoque
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'inventario_dispositivos'
    AND COLUMN_NAME  = 'em_estoque'
);
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE `inventario_dispositivos` ADD COLUMN `em_estoque` TINYINT(1) NOT NULL DEFAULT 0 COMMENT ''1 = parado no estoque para reutilizacao'' AFTER `apelido`',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- nome_responsavel
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'inventario_dispositivos'
    AND COLUMN_NAME  = 'nome_responsavel'
);
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE `inventario_dispositivos` ADD COLUMN `nome_responsavel` VARCHAR(150) DEFAULT NULL COMMENT ''Colaborador que usa o equipamento'' AFTER `em_estoque`',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- setor
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'inventario_dispositivos'
    AND COLUMN_NAME  = 'setor'
);
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE `inventario_dispositivos` ADD COLUMN `setor` VARCHAR(100) DEFAULT NULL COMMENT ''Departamento do responsavel'' AFTER `nome_responsavel`',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- localizacao_cpe
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'inventario_dispositivos'
    AND COLUMN_NAME  = 'localizacao_cpe'
);
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE `inventario_dispositivos` ADD COLUMN `localizacao_cpe` VARCHAR(100) DEFAULT NULL COMMENT ''Unidade CPE onde o equipamento esta fisicamente'' AFTER `setor`',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Índice para filtros rápidos por em_estoque
SET @idx_exists := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'inventario_dispositivos'
    AND INDEX_NAME   = 'idx_em_estoque'
);
SET @sql := IF(@idx_exists = 0,
  'ALTER TABLE `inventario_dispositivos` ADD INDEX `idx_em_estoque` (`em_estoque`)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
