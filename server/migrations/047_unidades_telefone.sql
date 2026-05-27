-- =====================================================================
-- Migration 047 - Telefone da unidade CPE
-- =====================================================================
-- Adicionado para aparecer no e-mail de confirmacao do agendamento
-- (modulo Equipe de Suporte). Cada unidade tem seu telefone, exibido
-- no e-mail que o cliente recebe quando a equipe confirma o atendimento.
-- =====================================================================

ALTER TABLE `unidades_cpe`
  ADD COLUMN `telefone` VARCHAR(40) DEFAULT NULL
      COMMENT 'Telefone de contato da unidade (exibido em e-mails ao cliente)'
      AFTER `endereco`;
