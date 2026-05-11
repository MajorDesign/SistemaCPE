-- ============================================================
-- MÓDULO DE MONITORAMENTO DE REDE — Migration 031
-- Data: 2026-05-11
-- Descrição: Unidades Mikrotik monitoradas + histórico de status
-- por WAN. Conexão via API REST do Mikrotik no /30 do WG_MATRIZ.
-- ============================================================

USE cpe_plus;

-- ─── Unidades cadastradas (cada uma com seu Mikrotik) ────────
CREATE TABLE IF NOT EXISTS network_units (
    id            INT NOT NULL AUTO_INCREMENT,
    -- Nome amigável que aparece no painel
    nome          VARCHAR(80)  NOT NULL,
    -- Identity exata do Mikrotik (ex: 'MK-MATRIZ', 'RAJA1570')
    identity      VARCHAR(80)  NOT NULL,
    -- IP que o servidor alcança via WG (ex: 10.16.14.2)
    host          VARCHAR(60)  NOT NULL,
    -- Porta da API (8728 padrão, 8729 com TLS)
    porta         INT          NOT NULL DEFAULT 8728,
    -- Identificadores das 2 WANs
    wan1_interface VARCHAR(50) DEFAULT 'ether1',
    wan1_label     VARCHAR(80) DEFAULT 'WAN 1',
    wan2_interface VARCHAR(50) DEFAULT 'ether2',
    wan2_label     VARCHAR(80) DEFAULT 'WAN 2',
    -- Metadata
    modelo        VARCHAR(80)  DEFAULT NULL,
    observacoes   TEXT         DEFAULT NULL,
    ativo         TINYINT(1)   NOT NULL DEFAULT 1,
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_identity (identity),
    KEY idx_ativo (ativo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ─── Histórico de status (snapshot a cada polling) ──────────
CREATE TABLE IF NOT EXISTS network_status_log (
    id          BIGINT NOT NULL AUTO_INCREMENT,
    unit_id     INT NOT NULL,
    wan_label   VARCHAR(80) NOT NULL,   -- ex: 'WAN1', 'WAN2'
    -- Status: 'online' | 'offline' | 'degraded' | 'unknown'
    status      VARCHAR(20) NOT NULL,
    latency_ms  DECIMAL(8,2) DEFAULT NULL,   -- latência média do ping
    packet_loss DECIMAL(5,2) DEFAULT NULL,   -- % perda
    rx_bps      BIGINT DEFAULT NULL,         -- tráfego download
    tx_bps      BIGINT DEFAULT NULL,         -- tráfego upload
    erro        VARCHAR(200) DEFAULT NULL,   -- mensagem se falha
    coletado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_unit_time (unit_id, coletado_em),
    KEY idx_status (status),
    CONSTRAINT fk_log_unit FOREIGN KEY (unit_id)
        REFERENCES network_units(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ─── Eventos críticos (queda detectada / lentidão) ──────────
CREATE TABLE IF NOT EXISTS network_events (
    id          BIGINT NOT NULL AUTO_INCREMENT,
    unit_id     INT NOT NULL,
    wan_label   VARCHAR(80) NOT NULL,
    tipo        ENUM('down','degraded','recovered') NOT NULL,
    descricao   VARCHAR(255) DEFAULT NULL,
    iniciado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    encerrado_em TIMESTAMP NULL DEFAULT NULL,
    duracao_seg INT DEFAULT NULL,
    notificado  TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_unit_iniciado (unit_id, iniciado_em DESC),
    KEY idx_ativos (encerrado_em),
    CONSTRAINT fk_event_unit FOREIGN KEY (unit_id)
        REFERENCES network_units(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ─── Seed das 5 unidades já mapeadas ────────────────────────
INSERT INTO network_units
    (nome, identity, host, porta, wan1_interface, wan1_label, wan2_interface, wan2_label, modelo, observacoes)
VALUES
    ('Matriz',         'MK-MATRIZ',     '10.16.0.1',  8728, 'ether1', 'WAN 1',        'ether2', 'WAN 2',        NULL,                            'Matriz - gateway central dos túneis WG'),
    ('Raja 1570',      'RAJA1570',      '10.16.12.2', 8728, 'ether1', 'CENTURY 1GB',  'ether2', 'ALGAR 1GB',    'CCR2004-16G-2S+',               'Raja - 2 WANs com IP público'),
    ('Rio Grande Norte','MK-CPERN',     '10.16.14.2', 8728, 'ether1', 'LINK 1',       'ether2', 'GOLDEN',       'RB4011iGS+5HacQ2HnD',           'CPE-RN'),
    ('Santa Catarina', 'MK-STCATARINA', '10.16.7.2',  8728, 'ether1', 'LINK 1',       'ether2', 'LINK 2',       'RB2011UiAS-2HnD',               'CPE-SC - investigar LINK-2 caído'),
    ('Paraná',         'MK-PARANA',     '10.16.6.2',  8728, 'ether1', 'LINK 1',       'ether2', 'LINK 2',       'RB2011UiAS-2HnD',               'CPE-PR - RouterOS 7.15 (atualizar) - LINK-2 caído')
ON DUPLICATE KEY UPDATE
    nome           = VALUES(nome),
    host           = VALUES(host),
    porta          = VALUES(porta),
    wan1_interface = VALUES(wan1_interface),
    wan1_label     = VALUES(wan1_label),
    wan2_interface = VALUES(wan2_interface),
    wan2_label     = VALUES(wan2_label),
    modelo         = VALUES(modelo),
    observacoes    = VALUES(observacoes);
