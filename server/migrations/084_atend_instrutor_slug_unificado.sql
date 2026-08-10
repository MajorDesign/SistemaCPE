-- ============================================================
-- MÓDULO ATENDIMENTOS - Migration 084
-- Data: 2026-08-05
-- Descrição: Agenda por instrutor + link direto + unificação
--   1) instrutor_id: dono da agenda (UNIQUE — 1 agenda por user).
--      NULL nas legadas (agendas de unidade — admin/resp continua gerenciando).
--   2) slug: URL amigável pro link direto de agendamento público
--      (ex: /agendar.html?agenda=mateus-carvalho).
--   3) oferece_presencial + oferece_online: substituem a restrição
--      antiga do campo `tipo` (que continua no banco por compat).
--      Toda agenda passa a oferecer as duas modalidades por padrão.
--   4) A capacidade unificada (1 slot = 1 vaga total) é feita no código
--      — cap_presencial/cap_online ficam no banco mas são ignorados
--      pelo _checar_vaga a partir de agora.
-- ============================================================

USE cpe_plus;

ALTER TABLE atend_agendas
  ADD COLUMN IF NOT EXISTS instrutor_id BIGINT NULL
    COMMENT 'User dono da agenda pessoal. NULL = agenda de unidade (admin gerencia).'
    AFTER unidade_id;

ALTER TABLE atend_agendas
  ADD COLUMN IF NOT EXISTS slug VARCHAR(60) NULL
    COMMENT 'URL amigável pro link direto público.'
    AFTER instrutor_id;

ALTER TABLE atend_agendas
  ADD COLUMN IF NOT EXISTS oferece_presencial TINYINT(1) NOT NULL DEFAULT 1
    COMMENT 'Substitui a restrição do antigo campo `tipo`.'
    AFTER slug;

ALTER TABLE atend_agendas
  ADD COLUMN IF NOT EXISTS oferece_online TINYINT(1) NOT NULL DEFAULT 1
    COMMENT 'Substitui a restrição do antigo campo `tipo`.'
    AFTER oferece_presencial;

-- Índices — UNIQUE em instrutor_id e slug.
-- Uso índice único regular (não sobre a coluna nullable como filtered),
-- porque MySQL/MariaDB aceita múltiplos NULLs em UNIQUE (comportamento SQL).
ALTER TABLE atend_agendas
  ADD UNIQUE INDEX IF NOT EXISTS uq_agenda_instrutor (instrutor_id);

ALTER TABLE atend_agendas
  ADD UNIQUE INDEX IF NOT EXISTS uq_agenda_slug (slug);

ALTER TABLE atend_agendas
  ADD CONSTRAINT fk_agenda_instrutor
    FOREIGN KEY (instrutor_id) REFERENCES users(id) ON DELETE SET NULL;
