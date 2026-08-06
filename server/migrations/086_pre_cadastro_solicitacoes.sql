-- ============================================================
-- MÓDULO PRÉ-CADASTRO - Migration 086
-- Data: 2026-08-06
-- Descrição: Fila de solicitações de liberação
--   Fluxo:
--     1. Usuário digita email na tela de login → /verificar-email
--     2. Email não está na whitelist (pre_cadastro_emails) → sistema oferece
--        "Enviar solicitação de pré-cadastro"
--     3. POST /solicitar-liberacao grava aqui (status='pendente')
--     4. Admin recebe notificação in-app + email
--     5. Admin libera → cria linha em pre_cadastro_emails + envia email
--        de confirmação pro usuário
--     6. Usuário volta e faz o fluxo normal (solicitar cadastro completo)
-- ============================================================

USE cpe_plus;

CREATE TABLE IF NOT EXISTS pre_cadastro_solicitacoes (
  id             INT PRIMARY KEY AUTO_INCREMENT,
  email          VARCHAR(190) NOT NULL,
  nome           VARCHAR(120) NULL COMMENT 'Nome do solicitante (opcional)',
  motivo         VARCHAR(500) NULL COMMENT 'Setor/motivo — texto livre',
  status         ENUM('pendente','liberado','recusado') NOT NULL DEFAULT 'pendente',
  respondido_por BIGINT NULL COMMENT 'Admin que aprovou/recusou',
  respondido_em  TIMESTAMP NULL,
  motivo_recusa  TEXT NULL,
  created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  INDEX idx_status (status),
  INDEX idx_email (email),
  CONSTRAINT fk_precad_sol_resp
    FOREIGN KEY (respondido_por) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Índice único parcial não é suportado no MariaDB — controle de duplicata é feito
-- no código: se já existe pendente pro email, retornar 400 (não criar duplicata).
