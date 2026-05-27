-- =====================================================================
-- Migration 050 - Equipamento many-to-many (curso e/ou treinamento)
-- =====================================================================
-- Pedido do usuario: o MESMO equipamento (ex: GNSS i80) pode ser usado
-- em varios cursos E varios treinamentos ao mesmo tempo.
--
-- Estrutura nova:
--   atend_equipamentos: catalogo global (sem servico_id)
--   atend_equipamento_vinculos: tabela de vinculo m:n
--     (equipamento_id, entidade='servico'|'treinamento', entidade_id)
--
-- Migracao de dados:
--   Cada equipamento existente com servico_id vira um vinculo
--   ('servico', servico_id), depois a coluna servico_id e dropada.
-- =====================================================================

-- 1) Cria tabela de vinculos m:n
CREATE TABLE IF NOT EXISTS `atend_equipamento_vinculos` (
  `equipamento_id` INT          NOT NULL,
  `entidade`       ENUM('servico','treinamento') NOT NULL,
  `entidade_id`    INT          NOT NULL,
  `created_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`equipamento_id`, `entidade`, `entidade_id`),
  KEY `idx_vinc_entidade` (`entidade`, `entidade_id`),
  CONSTRAINT `fk_vinc_equipamento`
    FOREIGN KEY (`equipamento_id`) REFERENCES `atend_equipamentos`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Vinculo m:n entre equipamento e curso/treinamento';

-- 2) Migra os equipamentos existentes — cada um vira UM vinculo de servico
INSERT IGNORE INTO `atend_equipamento_vinculos` (`equipamento_id`, `entidade`, `entidade_id`)
SELECT `id`, 'servico', `servico_id`
FROM `atend_equipamentos`
WHERE `servico_id` IS NOT NULL;

-- 3) Drop FK + coluna servico_id (equipamento agora e catalogo global)
ALTER TABLE `atend_equipamentos`
  DROP FOREIGN KEY `fk_atend_equip_servico`;

ALTER TABLE `atend_equipamentos`
  DROP KEY `idx_atend_equip_servico`,
  DROP COLUMN `servico_id`;

-- 4) Index pra ordenar/filtrar globalmente
ALTER TABLE `atend_equipamentos`
  ADD KEY `idx_equip_ativo` (`ativo`),
  ADD KEY `idx_equip_ordem` (`ordem`);
