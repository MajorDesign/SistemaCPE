-- =====================================================================
-- Migration 042 - Modulo Equipe de Suporte (agendas de atendimento)
-- =====================================================================
-- Agendas de atendimento (uma ou mais por unidade CPE), com horarios de
-- funcionamento configuraveis por dia da semana, slots gerados por
-- duracao fixa, agendamentos internos e bloqueios pontuais de horario.
--
-- Decisoes travadas com o usuario:
--  - Agenda e entidade propria, criada livremente (vinculo opcional a unidade)
--  - Agendamento e so interno (equipe de suporte) - sem link publico
--  - Horarios = slots fixos por duracao (configuravel por agenda)
--  - Menu "Equipe de Suporte", visivel a ADMIN e TI
-- =====================================================================

-- 1) Agendas de atendimento -------------------------------------------
CREATE TABLE IF NOT EXISTS `atend_agendas` (
  `id`               INT          NOT NULL AUTO_INCREMENT,
  `nome`             VARCHAR(150) NOT NULL,
  `unidade_id`       INT          DEFAULT NULL COMMENT 'Vinculo opcional com unidades_cpe',
  `descricao`        VARCHAR(500) DEFAULT NULL,
  `cor`              VARCHAR(7)   NOT NULL DEFAULT '#0d9488' COMMENT 'Cor da agenda no calendario',
  `slot_duracao_min` INT          NOT NULL DEFAULT 30 COMMENT 'Duracao de cada slot, em minutos',
  `ativo`            TINYINT(1)   NOT NULL DEFAULT 1,
  `created_by`       INT          DEFAULT NULL,
  `created_at`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_atend_agenda_nome` (`nome`),
  KEY `idx_atend_agenda_unidade` (`unidade_id`),
  KEY `idx_atend_agenda_ativo` (`ativo`),
  CONSTRAINT `fk_atend_agenda_unidade`
    FOREIGN KEY (`unidade_id`) REFERENCES `unidades_cpe` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Agendas de atendimento da equipe de suporte';

-- 2) Horarios de funcionamento (config por dia da semana) -------------
-- Um dia pode ter varias faixas (ex: Segunda 09:00-13:00 e 14:00-18:00).
CREATE TABLE IF NOT EXISTS `atend_horarios` (
  `id`          INT        NOT NULL AUTO_INCREMENT,
  `agenda_id`   INT        NOT NULL,
  `dia_semana`  TINYINT    NOT NULL COMMENT '0=Domingo, 1=Segunda ... 6=Sabado (JS getDay)',
  `hora_inicio` TIME       NOT NULL,
  `hora_fim`    TIME       NOT NULL,
  `ativo`       TINYINT(1) NOT NULL DEFAULT 1,
  `created_at`  DATETIME   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`  DATETIME   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_atend_horario_agenda_dia` (`agenda_id`, `dia_semana`),
  CONSTRAINT `fk_atend_horario_agenda`
    FOREIGN KEY (`agenda_id`) REFERENCES `atend_agendas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Faixas de funcionamento por dia da semana de cada agenda';

-- 3) Agendamentos (atendimentos) --------------------------------------
CREATE TABLE IF NOT EXISTS `atend_agendamentos` (
  `id`              INT           NOT NULL AUTO_INCREMENT,
  `agenda_id`       INT           NOT NULL,
  `titulo`          VARCHAR(200)  NOT NULL COMMENT 'Servico/assunto do atendimento',
  `cliente_nome`    VARCHAR(200)  DEFAULT NULL,
  `cliente_contato` VARCHAR(120)  DEFAULT NULL COMMENT 'Telefone ou e-mail do cliente',
  `observacoes`     VARCHAR(1000) DEFAULT NULL,
  `inicio`          DATETIME      NOT NULL,
  `fim`             DATETIME      NOT NULL,
  `status`          ENUM('agendado','atendido','cancelado','nao_compareceu')
                                  NOT NULL DEFAULT 'agendado',
  `created_by`      INT           DEFAULT NULL,
  `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_atend_agendamento_periodo` (`agenda_id`, `inicio`, `fim`, `status`),
  CONSTRAINT `fk_atend_agendamento_agenda`
    FOREIGN KEY (`agenda_id`) REFERENCES `atend_agendas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Atendimentos agendados - registro interno pela equipe de suporte';

-- 4) Bloqueios de horario ---------------------------------------------
CREATE TABLE IF NOT EXISTS `atend_bloqueios` (
  `id`         INT          NOT NULL AUTO_INCREMENT,
  `agenda_id`  INT          NOT NULL,
  `inicio`     DATETIME     NOT NULL,
  `fim`        DATETIME     NOT NULL,
  `motivo`     VARCHAR(255) DEFAULT NULL,
  `created_by` INT          DEFAULT NULL,
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_atend_bloqueio_periodo` (`agenda_id`, `inicio`, `fim`),
  CONSTRAINT `fk_atend_bloqueio_agenda`
    FOREIGN KEY (`agenda_id`) REFERENCES `atend_agendas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Bloqueios pontuais de horario (indisponibilidade)';

-- 5) Registro da pagina no sistema de permissoes ----------------------
INSERT INTO `permission_pages`
  (`page_key`, `display_name`, `description`, `category`, `icon`, `url`, `ordem`, `is_active`)
VALUES
  ('EQUIPE_SUPORTE', 'Equipe de Suporte',
   'Agendas de atendimento da equipe de suporte', 'operational',
   'bi-headset', '/SistemaCPE/web/pages/equipe-suporte.html', 81, 1)
ON DUPLICATE KEY UPDATE
  `display_name` = VALUES(`display_name`),
  `description`  = VALUES(`description`),
  `category`     = VALUES(`category`),
  `icon`         = VALUES(`icon`),
  `url`          = VALUES(`url`),
  `is_active`    = VALUES(`is_active`);

INSERT IGNORE INTO `permission_page_role` (`page_key`, `role`) VALUES
  ('EQUIPE_SUPORTE', 'ADMIN'),
  ('EQUIPE_SUPORTE', 'TI');
