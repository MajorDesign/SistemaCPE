-- =========================================================
-- 100_discord_notifications.sql
-- =========================================================
-- Sprint "Bot Discord Fase 4: notificacoes push" (2026-09-22):
--   Quando o solicitante de um ticket esta vinculado ao Discord, backend
--   insere linha aqui e o bot polla essa tabela a cada 15s pra mandar DM.
--
--   Fluxo:
--   1. Responsavel escreve resposta -> hook em criar_interacao chama
--      _notify_discord_if_linked(solicitante_id, 'resposta', ...)
--   2. Helper checa discord_links; se vinculado, INSERT aqui
--   3. Bot loop pega pending (delivered_at IS NULL), envia DM, marca
--      delivered_at (ou delivery_error se DM falhou)
--
--   Eventos:
--   - 'resposta'          -> responsavel comentou publicamente
--   - 'atribuido'         -> responsavel_id mudou (pego o chamado)
--   - 'status_changed'    -> status_id mudou (aberto->em andamento etc)
--   - 'ticket_resolvido'  -> status_id == 4, DM com botao "Avaliar"
--
--   payload_json guarda dados extras especificos do evento (autor da msg,
--   nome novo do responsavel, novo status label, etc) pra bot montar o
--   embed sem precisar re-consultar backend.

USE cpe_plus;

CREATE TABLE IF NOT EXISTS `discord_notifications_pending` (
  `id`             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `discord_id`     VARCHAR(32)     NOT NULL COMMENT 'Snowflake do destinatario no Discord',
  `ticket_id`      BIGINT UNSIGNED NOT NULL COMMENT 'FK tickets.id',
  `event_type`     ENUM('resposta','atribuido','status_changed','ticket_resolvido') NOT NULL,
  `payload_json`   TEXT            NULL     COMMENT 'JSON com dados extras do evento (autor, status_novo etc)',
  `created_at`     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `delivered_at`   DATETIME        NULL     COMMENT 'NULL enquanto nao entregue; timestamp quando bot enviou DM ok',
  `delivery_error` VARCHAR(255)    NULL     COMMENT 'Preenchido se DM falhou (user bloqueou bot etc)',
  PRIMARY KEY (`id`),
  KEY `idx_pending`     (`delivered_at`, `created_at`),
  KEY `idx_ticket`      (`ticket_id`),
  KEY `idx_discord`     (`discord_id`),
  CONSTRAINT `fk_notif_ticket`
    FOREIGN KEY (`ticket_id`) REFERENCES `tickets` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Fila de DMs Discord pendentes pro bot CPEControlBot enviar';
