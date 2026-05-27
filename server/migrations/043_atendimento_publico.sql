-- =====================================================================
-- Migration 043 - Equipe de Suporte: servicos, equipamentos e agendamento publico
-- =====================================================================
-- Continuacao do modulo (migration 042). Adiciona:
--  - Departamento + grupo "Comercial" (vendedores do form de agendamento)
--  - Instrucoes de agendamento na agenda
--  - Servicos/treinamentos por agenda (cada um com sua duracao)
--  - Equipamentos por servico (modelos exibidos conforme o servico escolhido)
--  - Campos do agendamento publico em atend_agendamentos + status 'pendente'
-- =====================================================================

-- 1) Departamento e grupo Comercial (idempotente) ---------------------
INSERT INTO `departments` (`name`, `description`)
SELECT 'Comercial', 'Departamento Comercial'
WHERE NOT EXISTS (SELECT 1 FROM `departments` WHERE `name` = 'Comercial');

INSERT INTO `cpe_grupo` (`department_id`, `name`, `description`, `visivel_signup`)
SELECT d.id, 'Comercial', 'Equipe comercial / vendedores', 1
FROM `departments` d
WHERE d.`name` = 'Comercial'
  AND NOT EXISTS (SELECT 1 FROM `cpe_grupo` WHERE `name` = 'Comercial');

-- 2) Instrucoes de agendamento na agenda ------------------------------
ALTER TABLE `atend_agendas`
  ADD COLUMN `instrucoes` VARCHAR(1000) DEFAULT NULL
    COMMENT 'Texto exibido ao cliente no formulario de agendamento'
    AFTER `descricao`;

-- 3) Servicos / treinamentos por agenda -------------------------------
CREATE TABLE IF NOT EXISTS `atend_servicos` (
  `id`          INT          NOT NULL AUTO_INCREMENT,
  `agenda_id`   INT          NOT NULL,
  `nome`        VARCHAR(150) NOT NULL,
  `duracao_min` INT          NOT NULL DEFAULT 60
                             COMMENT 'Duracao do atendimento desse servico, em minutos',
  `ativo`       TINYINT(1)   NOT NULL DEFAULT 1,
  `ordem`       INT          NOT NULL DEFAULT 0,
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_atend_servico_agenda` (`agenda_id`, `ativo`),
  CONSTRAINT `fk_atend_servico_agenda`
    FOREIGN KEY (`agenda_id`) REFERENCES `atend_agendas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Servicos/treinamentos oferecidos em cada agenda';

-- 4) Equipamentos por servico -----------------------------------------
CREATE TABLE IF NOT EXISTS `atend_equipamentos` (
  `id`         INT          NOT NULL AUTO_INCREMENT,
  `servico_id` INT          NOT NULL,
  `nome`       VARCHAR(150) NOT NULL,
  `ativo`      TINYINT(1)   NOT NULL DEFAULT 1,
  `ordem`      INT          NOT NULL DEFAULT 0,
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_atend_equip_servico` (`servico_id`, `ativo`),
  CONSTRAINT `fk_atend_equip_servico`
    FOREIGN KEY (`servico_id`) REFERENCES `atend_servicos` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Modelos de equipamento vinculados a cada servico';

-- 5) Campos do agendamento (publico + dados adicionais) ---------------
ALTER TABLE `atend_agendamentos`
  MODIFY COLUMN `status`
    ENUM('pendente','agendado','atendido','cancelado','nao_compareceu')
    NOT NULL DEFAULT 'pendente',
  ADD COLUMN `servico_id`       INT DEFAULT NULL                AFTER `agenda_id`,
  ADD COLUMN `equipamento_id`   INT DEFAULT NULL                AFTER `servico_id`,
  ADD COLUMN `cliente_email`    VARCHAR(190) DEFAULT NULL       AFTER `cliente_contato`,
  ADD COLUMN `cliente_telefone` VARCHAR(40)  DEFAULT NULL       AFTER `cliente_email`,
  ADD COLUMN `modalidade`       ENUM('presencial','online') DEFAULT NULL AFTER `observacoes`,
  ADD COLUMN `tipo_negocio`     ENUM('locacao','venda')     DEFAULT NULL AFTER `modalidade`,
  ADD COLUMN `vendedor_id`      BIGINT DEFAULT NULL             AFTER `tipo_negocio`,
  ADD COLUMN `origem`           ENUM('interno','publico') NOT NULL DEFAULT 'interno'
                                AFTER `created_by`,
  ADD KEY `idx_atend_agendamento_servico` (`servico_id`),
  ADD CONSTRAINT `fk_atend_agendamento_servico`
    FOREIGN KEY (`servico_id`) REFERENCES `atend_servicos` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `fk_atend_agendamento_equip`
    FOREIGN KEY (`equipamento_id`) REFERENCES `atend_equipamentos` (`id`) ON DELETE SET NULL;
