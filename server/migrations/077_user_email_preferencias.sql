-- ============================================================
-- MIGRATION 077: Preferencias de e-mail por usuario
-- Data: 2026-06-22
-- Descricao: Permite cada usuario optar OUT de receber determinado
-- tipo de email transacional. Default: tudo ativo (opt-in implicito).
--
-- Comportamento:
--   - SEM row pra (user_id, tipo_evento)  => ativo (envia)
--   - row.ativo = 1                       => ativo (envia)
--   - row.ativo = 0                       => opt-out (NAO envia)
--
-- Tipos de evento (alinhados aos templates de email_service.py):
--   ticket_criado            confirmacao pro solicitante
--   ticket_aberto_grupo      broadcast pro grupo (novo na fila)
--   ticket_atribuido         voce virou responsavel
--   ticket_status_alterado   status mudou
--   ticket_resposta_publica  nova resposta no chat
--   ticket_comentario_interno comentario interno (so equipe)
--   ticket_encaminhado       ticket vai pra outro grupo
--   ticket_devolvido         responsavel devolveu pra fila
--   ticket_reaberto          chamado reaberto
--   ticket_finalizado        chamado finalizado
-- ============================================================

USE cpe_plus;

CREATE TABLE IF NOT EXISTS user_email_preferencias (
  id          INT          NOT NULL AUTO_INCREMENT,
  user_id     INT          NOT NULL,
  tipo_evento VARCHAR(64)  NOT NULL,
  ativo       TINYINT(1)   NOT NULL DEFAULT 1,
  created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_user_tipo (user_id, tipo_evento),
  KEY idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
