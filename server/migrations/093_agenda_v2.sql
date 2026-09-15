-- =========================================================
-- 093_agenda_v2.sql — Agenda corporativa v2
-- =========================================================
-- Cria tabelas para agenda estilo Teams no desktop CPE Control:
--   ag_calendarios, ag_eventos, ag_participantes, ag_anexos,
--   ag_calendario_compartilhamentos, ag_evento_compartilhamentos,
--   ag_lembretes, ag_audit.
--
-- ADITIVA — nao altera nada existente. Rollback: DROP TABLE
-- na ordem inversa (foreign keys respeitadas).
--
-- Autor: 2026-09-14

-- --------------------------------------------------------
-- Calendarios: cada dono (user ou group) tem 1 default;
-- pode criar mais (projeto, treinamento) se quiser.
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS ag_calendarios (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  nome          VARCHAR(120) NOT NULL,
  cor           VARCHAR(7) NOT NULL DEFAULT '#1f6feb',
  tipo_dono     ENUM('user','group') NOT NULL,
  dono_user_id  BIGINT NULL,
  dono_group_id INT NULL,
  is_default    TINYINT(1) NOT NULL DEFAULT 0,
  descricao     TEXT NULL,
  criado_em     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  criado_por    BIGINT NOT NULL,
  deleted_at    DATETIME NULL,
  CONSTRAINT fk_ag_cal_user
    FOREIGN KEY (dono_user_id)  REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_ag_cal_group
    FOREIGN KEY (dono_group_id) REFERENCES cpe_grupo(id) ON DELETE CASCADE,
  CONSTRAINT fk_ag_cal_criador
    FOREIGN KEY (criado_por) REFERENCES users(id),
  CONSTRAINT ck_ag_cal_dono
    CHECK ((tipo_dono='user'  AND dono_user_id  IS NOT NULL AND dono_group_id IS NULL)
        OR (tipo_dono='group' AND dono_group_id IS NOT NULL AND dono_user_id  IS NULL)),
  INDEX idx_ag_cal_user  (dono_user_id, deleted_at),
  INDEX idx_ag_cal_group (dono_group_id, deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Eventos: pertencem a 1 calendario. Para aparecer em varios,
-- usar ag_evento_compartilhamentos.
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS ag_eventos (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  calendario_id   INT NOT NULL,
  titulo          VARCHAR(200) NOT NULL,
  descricao_html  MEDIUMTEXT NULL,
  local           VARCHAR(200) NULL,
  link_online     VARCHAR(500) NULL,
  meeting_code    VARCHAR(32) NULL,
  dia_inteiro     TINYINT(1) NOT NULL DEFAULT 0,
  inicio          DATETIME NOT NULL,
  fim             DATETIME NOT NULL,
  cor             VARCHAR(7) NULL,
  visibilidade    ENUM('publica','privada') NOT NULL DEFAULT 'privada',
  disponibilidade ENUM('livre','ocupado','provisorio','fora_escritorio') NOT NULL DEFAULT 'ocupado',
  status_op       ENUM('agendado','confirmado','em_andamento','concluido','cancelado') NOT NULL DEFAULT 'agendado',
  organizador_id  BIGINT NOT NULL,
  criado_em       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  criado_por      BIGINT NOT NULL,
  alterado_em     DATETIME NULL,
  alterado_por    BIGINT NULL,
  cancelado_em    DATETIME NULL,
  cancelado_por   BIGINT NULL,
  cancel_motivo   VARCHAR(500) NULL,
  deleted_at      DATETIME NULL,
  CONSTRAINT fk_ag_ev_cal
    FOREIGN KEY (calendario_id) REFERENCES ag_calendarios(id) ON DELETE CASCADE,
  CONSTRAINT fk_ag_ev_org
    FOREIGN KEY (organizador_id) REFERENCES users(id),
  CONSTRAINT fk_ag_ev_criador
    FOREIGN KEY (criado_por) REFERENCES users(id),
  CONSTRAINT ck_ag_ev_datas CHECK (fim >= inicio),
  INDEX idx_ag_ev_cal_periodo   (calendario_id, inicio, fim, deleted_at),
  INDEX idx_ag_ev_org           (organizador_id, inicio, deleted_at),
  INDEX idx_ag_ev_status_periodo (status_op, inicio)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Participantes: internos (user_id) OU externos (email+nome).
-- Externo recebe rsvp_token pra portal publico.
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS ag_participantes (
  id                 INT AUTO_INCREMENT PRIMARY KEY,
  evento_id          INT NOT NULL,
  user_id            BIGINT NULL,
  email_externo      VARCHAR(200) NULL,
  nome_externo       VARCHAR(120) NULL,
  papel              ENUM('organizador','obrigatorio','opcional') NOT NULL DEFAULT 'obrigatorio',
  rsvp               ENUM('sem_resposta','aceito','recusado','talvez') NOT NULL DEFAULT 'sem_resposta',
  respondido_em      DATETIME NULL,
  rsvp_token         CHAR(48) NULL,
  convite_enviado_em DATETIME NULL,
  criado_em          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_ag_par_ev
    FOREIGN KEY (evento_id) REFERENCES ag_eventos(id) ON DELETE CASCADE,
  CONSTRAINT fk_ag_par_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT ck_ag_par_id
    CHECK ((user_id IS NOT NULL AND email_externo IS NULL)
        OR (user_id IS NULL AND email_externo IS NOT NULL)),
  UNIQUE KEY uq_ag_par_ev_user   (evento_id, user_id),
  UNIQUE KEY uq_ag_par_ev_email  (evento_id, email_externo),
  UNIQUE KEY uq_ag_par_rsvp_tok  (rsvp_token),
  INDEX idx_ag_par_user (user_id, evento_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Anexos: PDF, planilha, imagem. Storage em disco (web/uploads/agenda).
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS ag_anexos (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  evento_id    INT NOT NULL,
  filename     VARCHAR(255) NOT NULL,
  storage_path VARCHAR(500) NOT NULL,
  mime         VARCHAR(120) NOT NULL,
  size_bytes   INT NOT NULL,
  uploaded_by  BIGINT NOT NULL,
  uploaded_em  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deleted_at   DATETIME NULL,
  CONSTRAINT fk_ag_anx_ev
    FOREIGN KEY (evento_id) REFERENCES ag_eventos(id) ON DELETE CASCADE,
  CONSTRAINT fk_ag_anx_user
    FOREIGN KEY (uploaded_by) REFERENCES users(id),
  INDEX idx_ag_anx_ev (evento_id, deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Compartilhamento de CALENDARIO inteiro (permanente ate revogar).
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS ag_calendario_compartilhamentos (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  calendario_id     INT NOT NULL,
  destino_tipo      ENUM('user','group') NOT NULL,
  destino_user_id   BIGINT NULL,
  destino_group_id  INT NULL,
  permissao         ENUM('disponibilidade','ler','editar') NOT NULL DEFAULT 'ler',
  concedido_por     BIGINT NOT NULL,
  concedido_em      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  revogado_em       DATETIME NULL,
  CONSTRAINT fk_ag_ccs_cal
    FOREIGN KEY (calendario_id) REFERENCES ag_calendarios(id) ON DELETE CASCADE,
  CONSTRAINT fk_ag_ccs_user
    FOREIGN KEY (destino_user_id)  REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_ag_ccs_group
    FOREIGN KEY (destino_group_id) REFERENCES cpe_grupo(id) ON DELETE CASCADE,
  CONSTRAINT ck_ag_ccs_dest
    CHECK ((destino_tipo='user'  AND destino_user_id  IS NOT NULL AND destino_group_id IS NULL)
        OR (destino_tipo='group' AND destino_group_id IS NOT NULL AND destino_user_id  IS NULL)),
  INDEX idx_ag_ccs_cal   (calendario_id, revogado_em),
  INDEX idx_ag_ccs_user  (destino_user_id, revogado_em),
  INDEX idx_ag_ccs_group (destino_group_id, revogado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Compartilhamento ad-hoc de UM evento.
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS ag_evento_compartilhamentos (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  evento_id         INT NOT NULL,
  destino_tipo      ENUM('user','group') NOT NULL,
  destino_user_id   BIGINT NULL,
  destino_group_id  INT NULL,
  concedido_por     BIGINT NOT NULL,
  concedido_em      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_ag_ecs_ev
    FOREIGN KEY (evento_id) REFERENCES ag_eventos(id) ON DELETE CASCADE,
  CONSTRAINT fk_ag_ecs_user
    FOREIGN KEY (destino_user_id)  REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_ag_ecs_group
    FOREIGN KEY (destino_group_id) REFERENCES cpe_grupo(id) ON DELETE CASCADE,
  CONSTRAINT ck_ag_ecs_dest
    CHECK ((destino_tipo='user'  AND destino_user_id  IS NOT NULL AND destino_group_id IS NULL)
        OR (destino_tipo='group' AND destino_group_id IS NOT NULL AND destino_user_id  IS NULL)),
  UNIQUE KEY uq_ag_ecs_ev_user   (evento_id, destino_user_id),
  UNIQUE KEY uq_ag_ecs_ev_group  (evento_id, destino_group_id),
  INDEX idx_ag_ecs_user  (destino_user_id),
  INDEX idx_ag_ecs_group (destino_group_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Lembretes agendados. V1 = 1 por evento (uq).
-- Tabela ja comporta N (uq esta em evento,user,offset).
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS ag_lembretes (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  evento_id     INT NOT NULL,
  user_id       BIGINT NOT NULL,
  offset_min    INT NOT NULL,
  disparar_em   DATETIME NOT NULL,
  disparado_em  DATETIME NULL,
  CONSTRAINT fk_ag_lm_ev
    FOREIGN KEY (evento_id) REFERENCES ag_eventos(id) ON DELETE CASCADE,
  CONSTRAINT fk_ag_lm_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE KEY uq_ag_lm (evento_id, user_id, offset_min),
  INDEX idx_ag_lm_scan (disparado_em, disparar_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Auditoria minima (V1). Historico de campos alterados fica V2.
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS ag_audit (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  evento_id     INT NOT NULL,
  actor_id      BIGINT NOT NULL,
  action        ENUM('created','updated','cancelled','deleted','participant_added',
                     'participant_removed','rsvp_changed','shared','attachment_added',
                     'attachment_removed') NOT NULL,
  metadata_json JSON NULL,
  criado_em     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_ag_au_ev
    FOREIGN KEY (evento_id) REFERENCES ag_eventos(id) ON DELETE CASCADE,
  CONSTRAINT fk_ag_au_user
    FOREIGN KEY (actor_id) REFERENCES users(id),
  INDEX idx_ag_au_ev (evento_id, criado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
