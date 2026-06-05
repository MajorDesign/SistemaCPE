-- =====================================================================
-- 074_grupo_drone_e_piloto.sql
-- Cria grupo "Drone" para os pilotos/operadores + campo piloto_id em
-- atend_agendamentos. Quando o agendamento for de drone, o admin escolhe
-- qual piloto (do grupo Drone) vai operar naquela data.
-- =====================================================================

USE `cpe_plus`;

-- 1) Grupo "Drone" — interno (visivel_signup=0, não aparece no primeiro acesso).
-- Department=1 (Suporte) — operadores de drone fazem parte do time técnico.
INSERT INTO `cpe_grupo` (`department_id`, `name`, `description`, `visivel_signup`)
SELECT 1, 'Drone', 'Pilotos e operadores de drone (uso interno)', 0
WHERE NOT EXISTS (SELECT 1 FROM `cpe_grupo` WHERE LOWER(`name`) = 'drone');

-- 2) Campo piloto_id em atend_agendamentos — soft FK para users.id.
-- Preenchido quando a oferta agendada for um drone.
ALTER TABLE `atend_agendamentos`
  ADD COLUMN `piloto_id` BIGINT NULL DEFAULT NULL AFTER `vendedor_nome`,
  ADD INDEX `idx_piloto` (`piloto_id`);
