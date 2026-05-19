-- =====================================================================
-- Migration 037 — Controle financeiro do estoque T.I. (inventario_itens)
--
-- Tabela onde o admin registra:
--   - Quanto vale cada item (notebook, mouse, cartucho, licenca, etc)
--   - Quantos itens tem
--   - Em qual unidade CPE / setor / localizacao
--   - Estoque minimo (alerta de reposicao)
--   - Vinculo OPCIONAL com inventario_dispositivos (notebook ja gerenciado
--     pelo agente). Quando vinculado, nome/marca herdados do dispositivo.
--
-- Item INATIVO = equipamento com defeito / baixado. Mantem o registro
-- para o relatorio de "valor parado / perda" com motivo declarado.
--
-- Idempotente.
-- =====================================================================

CREATE TABLE IF NOT EXISTS `inventario_itens` (
  `id`                       INT           NOT NULL AUTO_INCREMENT,
  `nome`                     VARCHAR(200)  NOT NULL,
  `codigo`                   VARCHAR(60)   DEFAULT NULL
                                           COMMENT 'SKU / codigo interno',
  `categoria`                ENUM('hardware','periferico','suprimento',
                                  'software','mobiliario','outro')
                                           NOT NULL DEFAULT 'outro',
  `descricao`                TEXT          DEFAULT NULL,
  `quantidade`               INT           NOT NULL DEFAULT 1,
  `valor_unitario`           DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  `estoque_minimo`           INT           NOT NULL DEFAULT 0
                                           COMMENT 'Alerta visual quando quantidade < estoque_minimo',
  `unidade_cpe`              VARCHAR(100)  DEFAULT NULL
                                           COMMENT 'Unidade fisica: BH, SP, Home Office, etc',
  `grupo_id`                 INT           DEFAULT NULL
                                           COMMENT 'FK cpe_grupo do setor responsavel',
  `localizacao_detalhe`      VARCHAR(150)  DEFAULT NULL
                                           COMMENT 'Sala/armario/posicao dentro da unidade',
  `dispositivo_id`           INT           DEFAULT NULL
                                           COMMENT 'FK opcional inventario_dispositivos (notebook com agente)',
  `ativo`                    TINYINT(1)    NOT NULL DEFAULT 1,
  `motivo_inativacao`        TEXT          DEFAULT NULL,
  `inativado_em`             DATETIME      DEFAULT NULL,
  `inativado_por_user_id`    INT           DEFAULT NULL,
  `criado_em`                DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em`            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                           ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_categoria`     (`categoria`),
  KEY `idx_ativo`         (`ativo`),
  KEY `idx_grupo`         (`grupo_id`),
  KEY `idx_unidade`       (`unidade_cpe`),
  KEY `idx_dispositivo`   (`dispositivo_id`),
  KEY `idx_codigo`        (`codigo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Controle financeiro do estoque T.I. (valor, quantidade, localizacao)';
