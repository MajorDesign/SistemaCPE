-- =========================================================
-- 098_users_cargo_telefone_ramal.sql
-- =========================================================
-- Sprint "Perfil de contato rico" (2026-09-17):
--   A tela de Pessoas do desktop mostra hoje so nome/email/setor/unidade.
--   Pra virar cartao de contato utilizavel (estilo Teams), precisamos
--   guardar tambem cargo/telefone/ramal do colaborador — colunas que
--   nao existem em users.
--
--   Regras de preenchimento:
--   - Cada usuario edita o proprio cargo/telefone/ramal via /users/me
--   - ADMIN/TI edita de qualquer um via /users/{id}
--   - Campos NULLABLE — mostrados no card so quando preenchidos
--
-- Aditiva. Zero mudanca em dados existentes.

USE cpe_plus;

ALTER TABLE users
  ADD COLUMN cargo    VARCHAR(120) NULL COMMENT 'Cargo/funcao do colaborador (ex: Analista de Suporte II)' AFTER role,
  ADD COLUMN telefone VARCHAR(30)  NULL COMMENT 'Telefone celular/direto (formato livre)' AFTER cargo,
  ADD COLUMN ramal    VARCHAR(10)  NULL COMMENT 'Ramal interno da unidade (ate 10 digitos)' AFTER telefone;
