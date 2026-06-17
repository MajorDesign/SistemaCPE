-- =====================================================================
-- 076_atend_modulos_e_banner.sql
-- Modulos e banner por entidade (servico, treinamento, drone).
--
-- 1) atend_modulos: tabela polimorfica, ordem livre dentro da entidade.
--    Topicos como JSON (lista simples de strings).
-- 2) banner_url: coluna em cada tabela de oferta, URL relativa pra
--    foto-destaque usada como hero no modal publico.
-- =====================================================================

USE `cpe_plus`;

CREATE TABLE IF NOT EXISTS `atend_modulos` (
  `id`          INT          NOT NULL AUTO_INCREMENT,
  `entidade`    ENUM('servico','treinamento','drone') NOT NULL,
  `entidade_id` INT          NOT NULL,
  `titulo`      VARCHAR(200) NOT NULL,
  `descricao`   TEXT         NULL,
  `duracao_min` INT          NULL COMMENT 'duracao do modulo em minutos',
  `topicos`     JSON         NULL COMMENT 'array JSON de strings com aulas/topicos internos',
  `ordem`       INT          NOT NULL DEFAULT 0,
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_modulos_entidade` (`entidade`, `entidade_id`, `ordem`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Modulos/aulas dos cursos, treinamentos e drones (uso publico)';

ALTER TABLE `atend_servicos`
  ADD COLUMN `banner_url` VARCHAR(500) NULL DEFAULT NULL
    COMMENT 'URL relativa do banner (hero do modal publico). NULL = usa 1a foto da galeria.';

ALTER TABLE `atend_treinamentos`
  ADD COLUMN `banner_url` VARCHAR(500) NULL DEFAULT NULL
    COMMENT 'URL relativa do banner. NULL = usa 1a foto da galeria.';

ALTER TABLE `atend_drones`
  ADD COLUMN `banner_url` VARCHAR(500) NULL DEFAULT NULL
    COMMENT 'URL relativa do banner. NULL = usa 1a foto da galeria.';
