-- ============================================================
-- MÓDULO DE RECEPÇÃO - Migration 014b (FIX)
-- Data: 2026-04-30
-- Descrição: Corrige tipos de FK em recepcao_reservas / recepcao_envios.
--   A migração 014 original definiu usuario_id / remetente_id como INT,
--   mas users.id é BIGINT. O CREATE TABLE falhava no FK constraint e
--   essas duas tabelas não eram criadas. Este script recria-as com o
--   tipo correto (BIGINT).
--
-- SEGURO: unidades_cpe e recepcao_salas não são tocadas — preserva os
-- dados já cadastrados nelas. As tabelas dropadas (reservas e envios)
-- ainda não tinham sido criadas com sucesso, então não há dados a perder.
-- ============================================================

USE cpe_plus;

DROP TABLE IF EXISTS recepcao_reservas;
DROP TABLE IF EXISTS recepcao_envios;

-- Reservas de sala (usuario_id agora é BIGINT — bate com users.id)
CREATE TABLE recepcao_reservas (
  id              INT PRIMARY KEY AUTO_INCREMENT,
  sala_id         INT NOT NULL,
  usuario_id      BIGINT NOT NULL,
  titulo          VARCHAR(200) NOT NULL,
  descricao       VARCHAR(500) DEFAULT NULL,
  inicio          DATETIME NOT NULL,
  fim             DATETIME NOT NULL,
  status          ENUM('pendente','confirmada','expirada','cancelada','concluida') DEFAULT 'pendente',
  confirmacao_prazo  DATETIME NOT NULL COMMENT 'created_at + 40min',
  confirmada_em      DATETIME DEFAULT NULL,
  cancelada_em       DATETIME DEFAULT NULL,
  motivo_cancel      VARCHAR(255) DEFAULT NULL,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (sala_id)    REFERENCES recepcao_salas(id) ON DELETE CASCADE,
  FOREIGN KEY (usuario_id) REFERENCES users(id),
  INDEX idx_reserva_sala_periodo (sala_id, inicio, fim, status),
  INDEX idx_reserva_status_prazo (status, confirmacao_prazo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Envios de mercadoria (remetente_id agora é BIGINT — bate com users.id)
CREATE TABLE recepcao_envios (
  id                  INT PRIMARY KEY AUTO_INCREMENT,
  remetente_id        BIGINT NOT NULL,
  destino             VARCHAR(255) NOT NULL,
  destinatario        VARCHAR(150) NOT NULL,
  valor_mercadoria    DECIMAL(12,2) DEFAULT 0,
  codigo_correios     VARCHAR(30) DEFAULT NULL,
  status_correios     VARCHAR(120) DEFAULT NULL,
  status_data         DATETIME DEFAULT NULL COMMENT 'data do último evento puxado dos Correios',
  status_local        VARCHAR(180) DEFAULT NULL,
  ultima_atualizacao  DATETIME DEFAULT NULL COMMENT 'quando consultamos os Correios pela última vez',
  observacoes         VARCHAR(500) DEFAULT NULL,
  created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (remetente_id) REFERENCES users(id),
  INDEX idx_envio_codigo (codigo_correios),
  INDEX idx_envio_remetente (remetente_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- FIM DA MIGRAÇÃO 014b (FIX)
-- ============================================================
