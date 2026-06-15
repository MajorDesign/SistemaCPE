-- =====================================================================
-- 075_fleet_reservation_data_fim.sql
-- Reserva contigua multi-dia: adiciona data_fim opcional em
-- fleet_reservations. Quando NULL, a reserva e de 1 dia (mesma data
-- de data_reserva), comportamento legado preservado.
--
-- Semantica: a reserva ocupa o veiculo continuamente de
--   (data_reserva, horario_inicio) ATE (COALESCE(data_fim, data_reserva), horario_fim).
-- =====================================================================

USE `cpe_plus`;

ALTER TABLE `fleet_reservations`
  ADD COLUMN `data_fim` DATE NULL DEFAULT NULL
    COMMENT 'NULL = reserva de 1 dia (=data_reserva); senao = ultimo dia da reserva contigua'
    AFTER `data_reserva`,
  ADD INDEX `idx_fleet_res_periodo` (`vehicle_id`, `status`, `data_reserva`, `data_fim`);
