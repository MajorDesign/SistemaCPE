-- =====================================================================
-- Migration 044 - Capacidade de atendimento por horario, por curso
-- =====================================================================
-- Cada curso passa a definir quantos clientes podem ser atendidos no
-- mesmo horario, separadamente por modalidade:
--   cap_presencial - default 1 (atendimento presencial costuma ser 1)
--   cap_online     - default 1 (o usuario aumenta conforme a operacao)
-- Presencial e online sao contados de forma independente (podem coexistir).
-- =====================================================================

ALTER TABLE `atend_servicos`
  ADD COLUMN `cap_presencial` INT NOT NULL DEFAULT 1
    COMMENT 'Maximo de atendimentos presenciais simultaneos no mesmo horario'
    AFTER `duracao_min`,
  ADD COLUMN `cap_online` INT NOT NULL DEFAULT 1
    COMMENT 'Maximo de atendimentos online simultaneos no mesmo horario'
    AFTER `cap_presencial`;
