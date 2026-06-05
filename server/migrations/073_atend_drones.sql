-- =====================================================================
-- 073_atend_drones.sql
-- Nova entidade "Drone" no modulo de atendimento. Espelho de
-- atend_treinamentos: cada drone pertence a uma agenda, tem capacidade,
-- duracao, instrutor, vendedor, etc. Diferenca: NAO entra na regra de
-- colisao curso<->treinamento (drone usa recurso fisico proprio).
--
-- Tabelas estendidas:
--   atend_equipamento_vinculos.entidade: adiciona 'drone'
--   atend_midia_fotos.entidade:          adiciona 'drone'
--   atend_midia_videos.entidade:         adiciona 'drone'
--   atend_agendamentos:                   nova coluna drone_id (FK soft)
-- =====================================================================

USE `cpe_plus`;

-- 1) Tabela principal de drones (espelho de atend_treinamentos)
CREATE TABLE IF NOT EXISTS `atend_drones` (
  `id`              INT NOT NULL AUTO_INCREMENT,
  `agenda_id`       INT NOT NULL,
  `nome`            VARCHAR(150) NOT NULL,
  `descricao`       TEXT NULL,
  `duracao_min`     INT NOT NULL DEFAULT 60,
  `cap_presencial`  INT NOT NULL DEFAULT 1,
  `cap_online`      INT NOT NULL DEFAULT 1,
  `instrutor`       VARCHAR(150) NULL,
  `vendedor_id`     BIGINT NULL,
  `vendedor_nome`   VARCHAR(150) NULL,
  `ativo`           TINYINT(1) NOT NULL DEFAULT 1,
  `ordem`           INT NOT NULL DEFAULT 0,
  `created_at`      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_agenda` (`agenda_id`),
  INDEX `idx_vendedor` (`vendedor_id`),
  INDEX `idx_ativo` (`ativo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2) Adiciona 'drone' ao enum de entidade em vinculos e midia
ALTER TABLE `atend_equipamento_vinculos`
  MODIFY COLUMN `entidade`
    ENUM('servico','treinamento','drone') NOT NULL;

ALTER TABLE `atend_midia_fotos`
  MODIFY COLUMN `entidade`
    ENUM('servico','treinamento','equipamento','drone') NOT NULL;

ALTER TABLE `atend_midia_videos`
  MODIFY COLUMN `entidade`
    ENUM('servico','treinamento','equipamento','drone') NOT NULL;

-- 3) Coluna drone_id em atend_agendamentos (igual servico_id / treinamento_id)
ALTER TABLE `atend_agendamentos`
  ADD COLUMN `drone_id` INT NULL DEFAULT NULL AFTER `treinamento_id`,
  ADD INDEX `idx_drone` (`drone_id`);
