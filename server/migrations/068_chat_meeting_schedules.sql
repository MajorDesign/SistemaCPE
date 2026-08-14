-- =====================================================================
-- Migration 068 (cpe_chat): agenda de reunioes
-- =====================================================================
-- Cada usuario administra sua propria agenda. Cliente externo recebe
-- email com link e token individual pra rastreio. Sala (chat_meeting_rooms)
-- e criada JUNTO com o agendamento — link vai estavel ate a reuniao rolar.
--
-- Lembretes 24h e 15min sao disparados por background job (APScheduler).
-- =====================================================================

USE `cpe_chat`;

CREATE TABLE IF NOT EXISTS `chat_meeting_schedules` (
  `id`              BIGINT       NOT NULL AUTO_INCREMENT,
  `meeting_id`      BIGINT       NULL COMMENT 'FK chat_meeting_rooms (sala do WebRTC)',
  `host_id`         BIGINT       NOT NULL COMMENT 'soft ref cpe_plus.users.id',
  `titulo`          VARCHAR(150) NOT NULL,
  `descricao`       TEXT         NULL,
  `start_at`        DATETIME     NOT NULL COMMENT 'inicio agendado (horario local BR)',
  `end_at`          DATETIME     NOT NULL COMMENT 'fim previsto (start + duracao)',
  `status`          ENUM('agendada','em_andamento','concluida','cancelada')
                    NOT NULL DEFAULT 'agendada',
  `cancelamento_motivo`      VARCHAR(300) NULL,
  `cancelado_por`            BIGINT       NULL COMMENT 'soft ref users.id',
  `cancelado_em`             DATETIME     NULL,
  `lembrete_24h_enviado_em`  DATETIME     NULL,
  `lembrete_15min_enviado_em` DATETIME    NULL,
  `created_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_msched_host_start`    (`host_id`, `start_at`),
  INDEX `idx_msched_status_start`  (`status`, `start_at`),
  INDEX `idx_msched_meeting`       (`meeting_id`),
  CONSTRAINT `fk_msched_meeting`
    FOREIGN KEY (`meeting_id`) REFERENCES `chat_meeting_rooms`(`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Convidados de uma reuniao agendada. Cada linha ganha um token unico
-- pra rastreamento (link personalizado no email). Se o convidado for
-- user interno do CPE, user_id preenchido; senao NULL (externo).
CREATE TABLE IF NOT EXISTS `chat_meeting_schedule_invitees` (
  `id`               BIGINT       NOT NULL AUTO_INCREMENT,
  `schedule_id`      BIGINT       NOT NULL,
  `nome`             VARCHAR(120) NOT NULL,
  `email`            VARCHAR(200) NOT NULL,
  `user_id`          BIGINT       NULL COMMENT 'soft ref cpe_plus.users.id se user interno',
  `token`            VARCHAR(64)  NOT NULL COMMENT 'token unico do convite (link personalizado)',
  `convite_enviado_em` DATETIME   NULL,
  `entrou_em`        DATETIME     NULL COMMENT 'quando o convidado entrou na sala',
  `created_at`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_invitee_token`   (`token`),
  INDEX `idx_invitee_schedule`    (`schedule_id`),
  INDEX `idx_invitee_email`       (`email`),
  CONSTRAINT `fk_invitee_schedule`
    FOREIGN KEY (`schedule_id`) REFERENCES `chat_meeting_schedules`(`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
