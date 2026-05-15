-- =====================================================================
-- Migration 034 — Inventário de celulares corporativos
--
-- Tabela para gestão de smartphones da empresa. Diferente dos computadores
-- (que usam o CPEAgente), celulares são cadastrados manualmente pelo admin
-- e atribuídos a um responsável que assina o termo de responsabilidade.
--
-- Adiciona também o campo cpf na tabela users — usado no termo e
-- preenchido uma única vez (não precisa redigitar a cada termo).
--
-- Idempotente: pode rodar múltiplas vezes sem erro.
-- =====================================================================

-- Campo CPF no usuário (usado no termo de responsabilidade)
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'users'
    AND COLUMN_NAME  = 'cpf'
);
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE `users` ADD COLUMN `cpf` VARCHAR(14) DEFAULT NULL COMMENT ''CPF do usuário (sem máscara, 11 dígitos)'' AFTER `email`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Tabela principal de celulares
CREATE TABLE IF NOT EXISTS `inventario_celulares` (
  `id`               INT           NOT NULL AUTO_INCREMENT,
  `marca`            VARCHAR(50)   NOT NULL,
  `modelo`           VARCHAR(100)  NOT NULL,
  `imei1`            VARCHAR(20)   NOT NULL,
  `imei2`            VARCHAR(20)   DEFAULT NULL,
  `numero_chip`      VARCHAR(30)   DEFAULT NULL,
  `operadora`        VARCHAR(30)   DEFAULT NULL,
  `numero_telefone`  VARCHAR(20)   DEFAULT NULL,
  `patrimonio`       VARCHAR(50)   DEFAULT NULL,
  `acessorios`       VARCHAR(255)  DEFAULT 'bateria e carregador' COMMENT 'Itens que acompanham o aparelho',
  `cor`              VARCHAR(30)   DEFAULT NULL,
  `status`           ENUM('em_uso','disponivel','manutencao','inativo') NOT NULL DEFAULT 'disponivel',
  `responsavel_id`   INT           DEFAULT NULL COMMENT 'users.id do responsável atual',
  `data_entrega`     DATE          DEFAULT NULL,
  `observacoes`      TEXT          DEFAULT NULL,
  `criado_em`        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em`    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_imei1` (`imei1`),
  KEY `idx_responsavel` (`responsavel_id`),
  KEY `idx_status`      (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Histórico de atribuições (quem teve o aparelho ao longo do tempo)
CREATE TABLE IF NOT EXISTS `inventario_celulares_historico` (
  `id`              INT       NOT NULL AUTO_INCREMENT,
  `celular_id`      INT       NOT NULL,
  `responsavel_id`  INT       NOT NULL,
  `data_entrega`    DATE      NOT NULL,
  `data_devolucao`  DATE      DEFAULT NULL,
  `observacoes`     TEXT      DEFAULT NULL,
  `termo_gerado_em` DATETIME  DEFAULT NULL,
  `registrado_em`   DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_celular`     (`celular_id`),
  KEY `idx_responsavel` (`responsavel_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
