-- =====================================================================
-- Migration 091 — atend_agendas.oferece_drones
--
-- Marca explicitamente quais agendas oferecem drones. O dropdown do
-- menu Drones passa a filtrar por essa flag (antes listava tudo).
--
-- Idempotente: usa INFORMATION_SCHEMA pra so alterar se coluna nao existe.
-- Backfill inicial: agendas que ja possuem drones cadastrados sao marcadas.
-- =====================================================================

SET @has_col := (
  SELECT COUNT(*)
    FROM information_schema.columns
   WHERE table_schema = DATABASE()
     AND table_name   = 'atend_agendas'
     AND column_name  = 'oferece_drones'
);

SET @ddl := IF(@has_col = 0,
  'ALTER TABLE `atend_agendas`
     ADD COLUMN `oferece_drones` TINYINT(1) NOT NULL DEFAULT 0
       COMMENT ''1 = agenda aparece no dropdown do menu Drones''
     AFTER `oferece_online`',
  'SELECT ''oferece_drones ja existe'' AS msg'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Backfill: agendas que ja tem drones ficam marcadas.
UPDATE `atend_agendas` a
   SET a.oferece_drones = 1
 WHERE a.oferece_drones = 0
   AND EXISTS (
     SELECT 1 FROM `atend_drones` d WHERE d.agenda_id = a.id
   );
