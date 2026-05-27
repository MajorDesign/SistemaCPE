-- =====================================================================
-- Migration 048 - Instrutor do curso/servico
-- =====================================================================
-- Quem vai dar o treinamento. Texto livre (nome do instrutor), exibido:
--   - na tabela de cursos do admin
--   - no e-mail de confirmacao enviado ao cliente
--   - no alerta de novo agendamento enviado pra equipe
--
-- Texto livre em vez de FK pra users porque o instrutor pode nao ter
-- conta no sistema (eng. terceirizado, parceiro). Evoluivel depois.
-- =====================================================================

ALTER TABLE `atend_servicos`
  ADD COLUMN `instrutor` VARCHAR(150) DEFAULT NULL
      COMMENT 'Nome do instrutor que ministra este curso (exibido ao cliente no e-mail)'
      AFTER `cap_online`;
