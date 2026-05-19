-- =====================================================================
-- Migration 036 — Manutenção de equipamentos T.I.
--
-- Cria 2 tabelas novas (fornecedores_ti + inventario_manutencoes) e
-- adiciona 2 colunas em inventario_dispositivos para sinalizar quando
-- um equipamento está fora para reparo.
--
-- Fluxo:
--   1. Admin cadastra fornecedor de TI (loja, assistência, etc).
--   2. Quando manda um notebook para reparo, abre uma manutenção
--      vinculada ao dispositivo. Notebook fica em_manutencao=1 e
--      manutencao_atual_id aponta para o registro aberto.
--   3. Quando o equipamento volta, fecha a manutenção (status=concluida,
--      data_retorno preenchido) e zera os flags do dispositivo.
--
-- Idempotente.
-- =====================================================================

-- ─── fornecedores_ti ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `fornecedores_ti` (
  `id`           INT          NOT NULL AUTO_INCREMENT,
  `nome`         VARCHAR(150) NOT NULL,
  `cnpj`         VARCHAR(18)  DEFAULT NULL,
  `endereco`     TEXT         DEFAULT NULL,
  `responsavel`  VARCHAR(150) DEFAULT NULL,
  `telefone`     VARCHAR(30)  DEFAULT NULL,
  `ativo`        TINYINT(1)   NOT NULL DEFAULT 1,
  `criado_em`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
                              ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_nome`  (`nome`),
  KEY `idx_ativo` (`ativo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Fornecedores de servicos de TI (manutencao, assistencia, etc)';

-- ─── inventario_manutencoes ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `inventario_manutencoes` (
  `id`                  INT           NOT NULL AUTO_INCREMENT,
  `dispositivo_id`      INT           DEFAULT NULL
                                      COMMENT 'NULL se equipamento nao esta no inventario',
  `marca`               VARCHAR(100)  DEFAULT NULL,
  `modelo`              VARCHAR(200)  DEFAULT NULL,
  `usuario_responsavel` VARCHAR(150)  DEFAULT NULL
                                      COMMENT 'Colaborador dono do equipamento',
  `problema`            TEXT          NOT NULL,
  `valor`               DECIMAL(10,2) DEFAULT NULL,
  `orcamento_path`      VARCHAR(255)  DEFAULT NULL
                                      COMMENT 'Caminho web do PDF de orcamento',
  `fornecedor_id`       INT           DEFAULT NULL,
  `status`              ENUM('orcamento','aprovada','em_andamento','concluida','cancelada')
                                      NOT NULL DEFAULT 'orcamento',
  `data_envio`          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `data_retorno`        DATETIME      DEFAULT NULL,
  `observacoes`         TEXT          DEFAULT NULL,
  `criado_em`           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em`       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                      ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_dispositivo` (`dispositivo_id`),
  KEY `idx_fornecedor`  (`fornecedor_id`),
  KEY `idx_status`      (`status`),
  KEY `idx_data_envio`  (`data_envio`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Historico de manutencoes de equipamentos T.I.';

-- ─── Colunas em inventario_dispositivos ────────────────────────────
-- em_manutencao
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'inventario_dispositivos'
    AND COLUMN_NAME  = 'em_manutencao'
);
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE `inventario_dispositivos` ADD COLUMN `em_manutencao` TINYINT(1) NOT NULL DEFAULT 0 COMMENT ''1 = equipamento esta com fornecedor para reparo'' AFTER `em_estoque`',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- manutencao_atual_id
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'inventario_dispositivos'
    AND COLUMN_NAME  = 'manutencao_atual_id'
);
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE `inventario_dispositivos` ADD COLUMN `manutencao_atual_id` INT DEFAULT NULL COMMENT ''FK para inventario_manutencoes da manutencao em aberto'' AFTER `em_manutencao`',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Índice em em_manutencao para filtros rápidos
SET @idx_exists := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'inventario_dispositivos'
    AND INDEX_NAME   = 'idx_em_manutencao'
);
SET @sql := IF(@idx_exists = 0,
  'ALTER TABLE `inventario_dispositivos` ADD INDEX `idx_em_manutencao` (`em_manutencao`)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
