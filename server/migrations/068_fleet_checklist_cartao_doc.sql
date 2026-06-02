-- =====================================================================
-- 068_fleet_checklist_cartao_doc.sql
-- Adiciona 4 colunas ao fleet_checklists pra registrar se o cartao de
-- combustivel e o documento do veiculo estavam dentro do carro tanto na
-- SAIDA quanto na DEVOLUCAO (retorno).
--
-- TINYINT(1):
--   NULL = nao informado (checklists antigos)
--   0    = NAO estava no carro
--   1    = SIM estava no carro
-- =====================================================================

USE `cpe_plus`;

ALTER TABLE `fleet_checklists`
  ADD COLUMN `cartao_combustivel_saida`   TINYINT(1) NULL AFTER `nivel_combustivel_saida`,
  ADD COLUMN `documento_veiculo_saida`    TINYINT(1) NULL AFTER `cartao_combustivel_saida`,
  ADD COLUMN `cartao_combustivel_retorno` TINYINT(1) NULL AFTER `nivel_combustivel_retorno`,
  ADD COLUMN `documento_veiculo_retorno`  TINYINT(1) NULL AFTER `cartao_combustivel_retorno`;
