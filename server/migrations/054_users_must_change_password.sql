-- =====================================================================
-- Migration 054 - Flag "forcar troca de senha no proximo login"
-- =====================================================================
-- Quando o admin reseta a senha de outro usuario, ele pode marcar essa
-- flag. No proximo login do usuario, o frontend mostra um alerta forte
-- pra trocar antes de continuar (UX nao bloqueante mas insistente).
--
-- Flag eh zerada automaticamente quando o proprio user troca a senha.
-- =====================================================================

ALTER TABLE `users`
  ADD COLUMN `must_change_password` TINYINT(1) NOT NULL DEFAULT 0
      COMMENT 'Se 1, frontend obriga troca de senha apos login (resetada por admin)'
      AFTER `password_hash`;
