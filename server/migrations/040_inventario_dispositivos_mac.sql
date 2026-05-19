-- =====================================================================
-- Migration 040 — MAC como identificador estavel de dispositivo
--
-- Hoje a chave logica de inventario_dispositivos eh `hostname` (UNIQUE).
-- Quando o usuario renomeia a maquina ou ela troca de rede (IP), o
-- agente acabaria criando registro novo no banco — gerando duplicatas
-- da mesma maquina fisica.
--
-- Solucao: adicionar `mac` (endereco MAC primario, formato AA:BB:CC:DD:EE:FF)
-- como chave estavel. O agente v1.6.0+ envia o MAC junto com o report,
-- e o backend faz upsert por MAC primeiro, hostname como fallback.
--
-- MULTIPLOS NULLs sao permitidos em UNIQUE no MariaDB/MySQL, entao
-- registros antigos (sem MAC) nao colidem entre si.
--
-- Idempotente.
-- =====================================================================

SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'inventario_dispositivos'
    AND COLUMN_NAME  = 'mac'
);
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE `inventario_dispositivos` ADD COLUMN `mac` VARCHAR(17) DEFAULT NULL COMMENT ''Endereco MAC primario — chave estavel quando hostname/IP mudam'' AFTER `hostname`',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- UNIQUE no MAC — permite multiplos NULL, mas impede dois registros com
-- mesmo MAC nao-nulo (impossivel ter 2 fisicamente)
SET @uniq_exists := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'inventario_dispositivos'
    AND INDEX_NAME   = 'uk_mac'
);
SET @sql := IF(@uniq_exists = 0,
  'ALTER TABLE `inventario_dispositivos` ADD UNIQUE KEY `uk_mac` (`mac`)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
