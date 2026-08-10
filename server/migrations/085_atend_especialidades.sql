-- ============================================================
-- MÓDULO ATENDIMENTOS - Migration 085
-- Data: 2026-08-05
-- Descrição: Especialidades de instrutor + assumir/transferir
--   1) atend_especialidades: catálogo (GNSS, Drone, Est. Total…)
--   2) atend_instrutor_especialidade: N:N instrutor × especialidade
--   3) atend_treinamentos.especialidade_id: cada treinamento aponta pra 1 especialidade
--   4) atend_agendamentos.instrutor_atribuido_id: quem "puxou" pra dar
--   Auto-popular: uma especialidade por nome distinto de treinamento existente,
--   e vincular cada treinamento à especialidade correspondente.
-- ============================================================

USE cpe_plus;

-- Catálogo de especialidades (tipos de treinamento)
CREATE TABLE IF NOT EXISTS atend_especialidades (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  nome        VARCHAR(120) NOT NULL UNIQUE,
  descricao   VARCHAR(500) NULL,
  ativo       TINYINT(1) NOT NULL DEFAULT 1,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- N:N instrutor × especialidade
CREATE TABLE IF NOT EXISTS atend_instrutor_especialidade (
  instrutor_id     BIGINT NOT NULL,
  especialidade_id INT    NOT NULL,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (instrutor_id, especialidade_id),
  INDEX idx_esp (especialidade_id),
  CONSTRAINT fk_ie_user FOREIGN KEY (instrutor_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_ie_esp  FOREIGN KEY (especialidade_id) REFERENCES atend_especialidades(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Treinamento aponta pra especialidade (opcional; NULL = ainda não classificado)
ALTER TABLE atend_treinamentos
  ADD COLUMN IF NOT EXISTS especialidade_id INT NULL
    COMMENT 'Especialidade requerida — usada pro matching de notificação'
    AFTER agenda_id,
  ADD INDEX IF NOT EXISTS idx_treino_esp (especialidade_id),
  ADD CONSTRAINT fk_treino_esp
    FOREIGN KEY (especialidade_id) REFERENCES atend_especialidades(id) ON DELETE SET NULL;

-- Instrutor "assumido" (puxou pra dar) — separa do piloto_id que é só drone
ALTER TABLE atend_agendamentos
  ADD COLUMN IF NOT EXISTS instrutor_atribuido_id BIGINT NULL
    COMMENT 'Instrutor que assumiu o agendamento (fluxo puxar)'
    AFTER piloto_id,
  ADD INDEX IF NOT EXISTS idx_ag_instrutor (instrutor_atribuido_id),
  ADD CONSTRAINT fk_ag_instrutor
    FOREIGN KEY (instrutor_atribuido_id) REFERENCES users(id) ON DELETE SET NULL;

-- ============================================================
-- SEED: uma especialidade por nome distinto de treinamento existente
-- + vincular cada treinamento à especialidade correspondente
-- ============================================================
INSERT IGNORE INTO atend_especialidades (nome)
  SELECT DISTINCT TRIM(nome) FROM atend_treinamentos
   WHERE nome IS NOT NULL AND TRIM(nome) <> '';

UPDATE atend_treinamentos t
  JOIN atend_especialidades e
    ON LOWER(TRIM(e.nome)) COLLATE utf8mb4_general_ci
     = LOWER(TRIM(t.nome)) COLLATE utf8mb4_general_ci
   SET t.especialidade_id = e.id
 WHERE t.especialidade_id IS NULL;
