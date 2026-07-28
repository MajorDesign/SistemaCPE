-- =====================================================================
-- Migration 082 - Modulo Comercial (agenda de vendedores + reunioes)
-- =====================================================================
-- Fase 1: base do modulo Comercial.
--
-- Decisoes travadas com o usuario (2026-07-17):
--  - Cada vendedor tem 3 slots por dia, DEFINIDOS por ele proprio (nao fixos)
--    Aplicam-se em todos os dias uteis. Slot vazio = disponivel pra marcacao.
--  - Qualquer pessoa do grupo Comercial pode marcar reuniao em qualquer vendedor
--  - Cliente com email igual e REUSADO (nao duplica) — historico junto
--  - Reuniao gera link publico usando a mesma infra de chat/meetings (Google Meet)
--  - Pos-reuniao: vendedor classifica quente/morno/frio + comentario
--  - Material de apoio: global (nao por vendedor), gerenciado por ADMIN/Resp Comercial
--
-- Idempotente: pode rodar multiplas vezes.
-- =====================================================================

-- =====================================================================
-- 1) SLOTS DE HORARIO DO VENDEDOR (3 por vendedor)
-- =====================================================================
CREATE TABLE IF NOT EXISTS `comercial_vendedor_slots` (
  `id`          INT          NOT NULL AUTO_INCREMENT,
  `vendedor_id` BIGINT       NOT NULL COMMENT 'FK users.id — quem eh o vendedor',
  `hora`        TIME         NOT NULL COMMENT 'ex: 09:00, 14:00, 17:00',
  `ordem`       TINYINT      NOT NULL COMMENT '1, 2 ou 3 (max 3 slots por vendedor)',
  `ativo`       TINYINT(1)   NOT NULL DEFAULT 1,
  `created_at`  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_vendedor_ordem` (`vendedor_id`, `ordem`),
  KEY `idx_vendedor` (`vendedor_id`),
  CONSTRAINT `fk_cvs_vendedor`
    FOREIGN KEY (`vendedor_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Horarios que cada vendedor atende (3 slots por dia)';

-- =====================================================================
-- 2) CLIENTES (reusa por email)
-- =====================================================================
CREATE TABLE IF NOT EXISTS `comercial_clientes` (
  `id`                 INT          NOT NULL AUTO_INCREMENT,
  `nome`               VARCHAR(200) NOT NULL,
  `empresa`            VARCHAR(200) DEFAULT NULL,
  `email`              VARCHAR(190) DEFAULT NULL,
  `telefone`           VARCHAR(30)  DEFAULT NULL,
  `produto_interesse`  TEXT         DEFAULT NULL COMMENT 'Campo aberto',
  `criado_por`         BIGINT       DEFAULT NULL,
  `created_at`         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_cliente_email` (`email`) COMMENT 'permite NULL duplicado; se tiver email, unico',
  KEY `idx_empresa` (`empresa`),
  KEY `idx_criado_por` (`criado_por`),
  CONSTRAINT `fk_cc_criado_por`
    FOREIGN KEY (`criado_por`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Cadastro de clientes do comercial (dedup por email)';

-- =====================================================================
-- 3) REUNIOES (agendamento no slot do vendedor)
-- =====================================================================
CREATE TABLE IF NOT EXISTS `comercial_reunioes` (
  `id`               INT          NOT NULL AUTO_INCREMENT,
  `vendedor_id`      BIGINT       NOT NULL COMMENT 'Vendedor que vai atender',
  `cliente_id`       INT          NOT NULL,
  `data`             DATE         NOT NULL,
  `hora`             TIME         NOT NULL COMMENT 'Copia do slot escolhido (snapshot)',
  `slot_id`          INT          DEFAULT NULL COMMENT 'FK opcional pra vendedor_slots — pode ser NULL se slot foi deletado',
  `status`           ENUM('agendada','realizada','cancelada','nao_compareceu') NOT NULL DEFAULT 'agendada',
  `meeting_url`      VARCHAR(500) DEFAULT NULL COMMENT 'link publico Google Meet (via chat/meetings)',
  `meeting_id`       INT          DEFAULT NULL COMMENT 'FK chat_meetings.id (nao FK real pra evitar cascade)',
  `agendado_por`     BIGINT       NOT NULL COMMENT 'user que criou a reuniao (do grupo Comercial)',
  `agendado_em`      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `classificacao`    ENUM('quente','morno','frio') DEFAULT NULL COMMENT 'preenchido pos-reuniao',
  `comentario`       TEXT         DEFAULT NULL COMMENT 'observacao pos-reuniao',
  `classificado_em`  TIMESTAMP    NULL DEFAULT NULL COMMENT 'MariaDB 10.4: NULL explicito obrigatorio',
  `updated_at`       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_vendedor_data` (`vendedor_id`, `data`),
  KEY `idx_cliente` (`cliente_id`),
  KEY `idx_status` (`status`),
  KEY `idx_data` (`data`),
  CONSTRAINT `fk_cr_vendedor`
    FOREIGN KEY (`vendedor_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_cr_cliente`
    FOREIGN KEY (`cliente_id`) REFERENCES `comercial_clientes` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_cr_slot`
    FOREIGN KEY (`slot_id`) REFERENCES `comercial_vendedor_slots` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_cr_agendado_por`
    FOREIGN KEY (`agendado_por`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Reunioes agendadas de vendedores com clientes';

-- Nota: NAO ha UNIQUE (vendedor_id, data, hora) pra permitir reagendamento
-- apos cancelamento. Backend valida "slot ocupado" antes de criar/mover.

-- =====================================================================
-- 4) MATERIAL DE APOIO (arquivos globais pra reuniao)
-- =====================================================================
CREATE TABLE IF NOT EXISTS `comercial_material_apoio` (
  `id`                    INT           NOT NULL AUTO_INCREMENT,
  `titulo`                VARCHAR(200)  NOT NULL,
  `descricao`             TEXT          DEFAULT NULL,
  `arquivo_path`          VARCHAR(500)  NOT NULL COMMENT 'ex: /SistemaCPE/web/uploads/comercial/xxx.pdf',
  `arquivo_nome_original` VARCHAR(255)  DEFAULT NULL,
  `mime_type`             VARCHAR(80)   DEFAULT NULL,
  `tamanho_bytes`         BIGINT        DEFAULT NULL,
  `categoria`             VARCHAR(50)   DEFAULT NULL COMMENT 'apresentacao/tabela/video/outro',
  `ordem`                 INT           NOT NULL DEFAULT 0,
  `ativo`                 TINYINT(1)    NOT NULL DEFAULT 1,
  `uploaded_by`           BIGINT        DEFAULT NULL,
  `created_at`            TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`            TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_ativo` (`ativo`),
  KEY `idx_categoria` (`categoria`),
  KEY `idx_ordem` (`ordem`),
  CONSTRAINT `fk_cma_uploaded_by`
    FOREIGN KEY (`uploaded_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Arquivos globais que vendedores usam durante reunioes';

-- =====================================================================
-- 5) REGISTRO NO SISTEMA DE PERMISSOES
--    Menu "Comercial" liberado pra:
--      - Todos do grupo Comercial (via permission_page_group)
--      - ADMIN, TI, MANAGER (via permission_page_role)
-- =====================================================================
INSERT INTO `permission_pages`
  (`page_key`, `display_name`, `description`, `category`, `icon`, `url`, `ordem`, `is_active`)
VALUES
  ('COMERCIAL', 'Comercial',
   'Agenda de vendedores, marcacao de reunioes, cadastro de clientes e material de apoio',
   'operational', 'bi-briefcase-fill',
   '/SistemaCPE/web/pages/comercial.html', 65, 1)
ON DUPLICATE KEY UPDATE
  `display_name` = VALUES(`display_name`),
  `description`  = VALUES(`description`),
  `icon`         = VALUES(`icon`),
  `url`          = VALUES(`url`),
  `is_active`    = 1;

-- Roles com acesso irrestrito (ADMIN, TI, MANAGER)
INSERT IGNORE INTO `permission_page_role` (`page_key`, `role`) VALUES
  ('COMERCIAL', 'ADMIN'),
  ('COMERCIAL', 'TI'),
  ('COMERCIAL', 'MANAGER');

-- Grupo Comercial ganha acesso (subquery pega ID sem hard-code)
INSERT IGNORE INTO `permission_page_group` (`page_key`, `group_id`)
SELECT 'COMERCIAL', id FROM `cpe_grupo` WHERE LOWER(name) = 'comercial' LIMIT 1;

-- =====================================================================
-- FIM Migration 082
-- =====================================================================
