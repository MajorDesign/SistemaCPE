-- =====================================================================
-- Migration 051 - Agendamento pode referenciar treinamento
-- =====================================================================
-- Pra cliente poder agendar tanto um curso quanto um treinamento:
--   atend_agendamentos.servico_id (ja existe)    -> aponta atend_servicos
--   atend_agendamentos.treinamento_id (novo)     -> aponta atend_treinamentos
--
-- Cada agendamento usa UM dos dois (XOR). A logica que valida vaga e
-- capacidade (cap_presencial/cap_online) le do registro correto.
-- =====================================================================

ALTER TABLE `atend_agendamentos`
  ADD COLUMN `treinamento_id` INT NULL
      COMMENT 'FK atend_treinamentos — exclusivo com servico_id'
      AFTER `servico_id`,
  ADD KEY `idx_atend_agendamento_treino` (`treinamento_id`),
  ADD CONSTRAINT `fk_atend_agendamento_treino`
      FOREIGN KEY (`treinamento_id`) REFERENCES `atend_treinamentos`(`id`) ON DELETE SET NULL;
