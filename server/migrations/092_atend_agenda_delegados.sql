-- =====================================================================
-- Migration 092 — atend_agenda_delegados
--
-- Delegacao granular: admin autoriza usuario X a operar SOBRE a agenda Y
-- sem precisar dar admin global de suporte. Delegado pode:
--   - editar dados da agenda (nome, cor, horarios, config)
--   - criar/editar/cancelar atendimentos na agenda
--   - bloquear/desbloquear horarios da agenda
-- NAO pode: cadastrar cursos/treinamentos/drones (fica com admin),
--          adicionar outros delegados, excluir a agenda inteira.
--
-- Idempotente: CREATE IF NOT EXISTS.
-- =====================================================================

CREATE TABLE IF NOT EXISTS `atend_agenda_delegados` (
  `agenda_id`  INT       NOT NULL,
  `user_id`    BIGINT    NOT NULL,
  `granted_by` BIGINT    DEFAULT NULL COMMENT 'Admin que concedeu o acesso',
  `granted_at` DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`agenda_id`, `user_id`),
  KEY `idx_atend_deleg_user` (`user_id`),
  CONSTRAINT `fk_atend_deleg_agenda`
    FOREIGN KEY (`agenda_id`) REFERENCES `atend_agendas` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_atend_deleg_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Usuarios autorizados a operar agendas especificas (granular)';
