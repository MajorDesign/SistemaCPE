-- =====================================================================
-- 062_chat_presence_estendido.sql
-- Amplia o enum de chat_presence.status pra suportar status manual
-- estilo Discord (Disponivel / Ausente / Nao Perturbar / Invisivel).
--
-- - online      : conectado e disponivel (default ao abrir o app)
-- - ausente     : auto-aplicado apos N min de inatividade, ou manual
-- - dnd         : nao perturbar — suprime sons/notifs
-- - invisivel   : aparece como offline pros outros mas pode usar tudo
-- - offline     : WS desconectado
-- =====================================================================

USE `cpe_chat`;

ALTER TABLE `chat_presence`
  MODIFY `status` ENUM('online','ausente','dnd','invisivel','offline')
  NOT NULL DEFAULT 'offline';

-- Coluna nova: status MANUAL escolhido pelo user (vs status automatico
-- gerado pelo WS connect/disconnect). Se NULL, usa o automatico.
ALTER TABLE `chat_presence`
  ADD COLUMN `status_manual` ENUM('online','ausente','dnd','invisivel') NULL DEFAULT NULL
    COMMENT 'Status escolhido pelo user manualmente — sobrepoe o automatico'
    AFTER `status`;
