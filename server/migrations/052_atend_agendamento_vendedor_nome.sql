-- =====================================================================
-- Migration 052 - Vendedor "manual" no agendamento publico
-- =====================================================================
-- Quando o cliente nao encontra o vendedor que o atende na lista
-- (vendedores = users do grupo Comercial), ele pode digitar o nome
-- livremente. Esse nome fica em atend_agendamentos.vendedor_nome.
--
-- Regra de exibicao em listings/e-mails:
--   COALESCE(users.name via vendedor_id, vendedor_nome) AS vendedor
-- =====================================================================

ALTER TABLE `atend_agendamentos`
  ADD COLUMN `vendedor_nome` VARCHAR(150) NULL
      COMMENT 'Nome livre do vendedor quando o cliente nao achou na lista'
      AFTER `vendedor_id`;
