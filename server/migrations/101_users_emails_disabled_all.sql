-- =========================================================
-- 101_users_emails_disabled_all.sql
-- =========================================================
-- Master switch de opt-out de emails transacionais (2026-09-22).
--
-- Motivador: usuarios que sao ADMIN + RESPONSAVEL_GRUPO de varios grupos
-- reclamaram do volume de email. Preferencias por tipo (migration antiga
-- user_email_preferencias) resolvem parcialmente, mas se algum tipo NOVO
-- for adicionado ao TIPOS_EVENTO_EMAIL, esse tipo chega ativo por default
-- e o user precisa desligar de novo.
--
-- Solucao: flag master (1=off) checada ANTES das preferencias por tipo.
-- Se ligada, o backend nao envia NENHUM email transacional pra este user.
-- Notificacoes no sino (in-app) e no Discord seguem funcionando normal
-- — este switch e SO pra email.
--
-- Aditiva. Zero mudanca em dados existentes.

USE cpe_plus;

ALTER TABLE users
  ADD COLUMN emails_disabled_all TINYINT(1) NOT NULL DEFAULT 0
    COMMENT 'Master opt-out: 1 = user nao recebe NENHUM email transacional (sino/Discord seguem)'
    AFTER is_active;
