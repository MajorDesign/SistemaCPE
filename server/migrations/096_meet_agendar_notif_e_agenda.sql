-- =========================================================
-- 096_meet_agendar_notif_e_agenda.sql
-- =========================================================
-- Sprint "Agendar reuniao" (2026-09-15):
--  1. notificacoes.link_alvo — URL alvo pra abrir ao clicar no sino
--     (tickets ja usavam /ticket-detail.html?id=X hardcoded no front;
--      reuniao precisa apontar pra meet.html?code=... — variavel).
--  2. chat_meeting_schedules.agenda_evento_id — FK soft pro ag_eventos
--     da Agenda V2, pra manter espelhamento e permitir update/delete
--     em cascata quando o host edita o schedule.
--
-- Aditiva. Zero mudanca em dados.

-- ----- 1) DB cpe_plus: notificacoes.link_alvo -----
USE cpe_plus;

ALTER TABLE notificacoes
  ADD COLUMN link_alvo VARCHAR(500) NULL AFTER tipo;

-- ----- 2) DB cpe_chat: chat_meeting_schedules.agenda_evento_id -----
USE cpe_chat;

ALTER TABLE chat_meeting_schedules
  ADD COLUMN agenda_evento_id INT NULL AFTER meeting_id;

CREATE INDEX idx_sched_agenda_evento
  ON chat_meeting_schedules (agenda_evento_id);
