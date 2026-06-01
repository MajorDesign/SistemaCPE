-- =====================================================================
-- 065_user_avatar.sql
-- Adiciona coluna avatar_url na tabela cpe_plus.users — URL relativa
-- pra foto de perfil. Foto fica em web/uploads/user-avatars/<id>-<uuid>.<ext>.
-- NULL = sem foto (UI mostra iniciais).
-- =====================================================================

USE `cpe_plus`;

ALTER TABLE `users`
  ADD COLUMN `avatar_url` VARCHAR(255) NULL
    COMMENT 'URL relativa da foto de perfil (web/uploads/user-avatars/...)';
