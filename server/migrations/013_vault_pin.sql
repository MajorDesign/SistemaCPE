-- ============================================================
-- Migração 013: PIN do Cofre de Senhas
-- ============================================================
-- Adiciona a coluna vault_pin_hash na tabela users para o
-- recurso de "PIN privado" do Cofre de Senhas — bcrypt hash
-- do PIN escolhido pelo usuário para desbloquear suas senhas
-- privadas (exclusivas).
--
-- A coluna nasce NULL: usuário sem PIN cadastrado (ainda) não
-- tem cofre privado desbloqueado. ADMIN pode resetar para NULL
-- via /api/passwords/vault-pin/reset.
-- ============================================================

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS vault_pin_hash VARCHAR(255) DEFAULT NULL
    COMMENT 'Hash bcrypt do PIN do Cofre de Senhas (NULL = sem PIN cadastrado)';
