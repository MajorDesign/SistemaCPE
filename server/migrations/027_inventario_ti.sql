-- =====================================================================
-- Migration 027 — Módulo Inventário T.I.
--
-- Cria a tabela de dispositivos monitorados por agente.
-- O agente Python instalado nas máquinas envia relatórios via POST
-- /api/inventario/agent/report e os dados são upsertados aqui.
--
-- Status online/offline é calculado dinamicamente pelo backend:
--   online  → ultimo_heartbeat ≤ 10 minutos atrás
--   offline → caso contrário (ou NULL)
--
-- Idempotente: pode rodar múltiplas vezes sem erro.
-- =====================================================================

CREATE TABLE IF NOT EXISTS `inventario_dispositivos` (
  `id`                  INT           NOT NULL AUTO_INCREMENT,
  `hostname`            VARCHAR(100)  NOT NULL,
  `apelido`             VARCHAR(100)  DEFAULT NULL          COMMENT 'Apelido/Patrimônio — editável pelo admin',
  `usuario_logado`      VARCHAR(150)  DEFAULT NULL,
  `ip_interno`          VARCHAR(45)   DEFAULT NULL,
  `ip_externo`          VARCHAR(45)   DEFAULT NULL,
  `tipo`                ENUM('notebook','desktop','servidor','terminal','outro')
                                      NOT NULL DEFAULT 'notebook',
  `marca`               VARCHAR(100)  DEFAULT NULL,
  `modelo`              VARCHAR(200)  DEFAULT NULL,
  `numero_serie`        VARCHAR(150)  DEFAULT NULL,
  `sistema_operacional` VARCHAR(200)  DEFAULT NULL,
  `versao_os`           VARCHAR(200)  DEFAULT NULL,
  `arquitetura`         VARCHAR(20)   DEFAULT NULL,
  -- Memória RAM
  `memoria_total_gb`    DECIMAL(8,2)  DEFAULT NULL,
  `memoria_uso_pct`     DECIMAL(5,2)  DEFAULT NULL,
  -- Disco (agregado; detalhe por partição em discos_json)
  `disco_total_gb`      DECIMAL(10,2) DEFAULT NULL,
  `disco_livre_gb`      DECIMAL(10,2) DEFAULT NULL,
  `disco_livre_pct`     DECIMAL(5,2)  DEFAULT NULL,
  `discos_json`         TEXT          DEFAULT NULL          COMMENT 'JSON com detalhes por partição',
  -- CPU
  `cpu_modelo`          VARCHAR(200)  DEFAULT NULL,
  `cpu_nucleos`         INT           DEFAULT NULL,
  `cpu_uso_pct`         DECIMAL(5,2)  DEFAULT NULL,
  -- Uptime
  `dias_ligado`         INT           DEFAULT NULL,
  -- Geolocalização por IP
  `estado_br`           VARCHAR(100)  DEFAULT NULL,
  `cidade`              VARCHAR(100)  DEFAULT NULL,
  -- Metadados do agente
  `versao_agente`       VARCHAR(20)   DEFAULT NULL,
  `ultimo_heartbeat`    DATETIME      DEFAULT NULL,
  `criado_em`           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em`       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_hostname` (`hostname`),
  KEY `idx_tipo`            (`tipo`),
  KEY `idx_estado`          (`estado_br`),
  KEY `idx_heartbeat`       (`ultimo_heartbeat`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Dispositivos monitorados pelo Agente de Inventário T.I. CPE';
