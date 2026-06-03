-- =====================================================================
-- 072_pre_cadastro_cpf_unit.sql
-- Adiciona CPF (obrigatorio) e unit_id (obrigatorio) no pre-cadastro.
-- Usuario escolhe estes dois ao se solicitar (alem do username, que ja
-- existia na tabela mas era gerado server-side — agora vira choice do
-- usuario tambem).
-- =====================================================================

USE `cpe_plus`;

ALTER TABLE `pre_cadastro_pendentes`
  ADD COLUMN `cpf` VARCHAR(14) NULL COMMENT 'CPF informado pelo usuario, formato 000.000.000-00 ou apenas digitos' AFTER `name`,
  ADD COLUMN `unit_id` INT NULL COMMENT 'soft ref unidades_cpe.id — unidade escolhida pelo usuario' AFTER `group_id`,
  ADD INDEX `idx_unit_id` (`unit_id`),
  ADD INDEX `idx_cpf` (`cpf`);
