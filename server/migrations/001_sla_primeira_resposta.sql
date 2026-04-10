-- ============================================================
-- Migration 001: SLA de Primeira Resposta + SLA em Subcategorias
-- Executar no banco cpe_plus
-- ============================================================

-- 1. Adicionar sla_primeira_resposta_minutos na tabela categorias
ALTER TABLE `categorias`
  ADD COLUMN `sla_primeira_resposta_minutos` INT UNSIGNED DEFAULT NULL
  COMMENT 'SLA de primeira resposta em minutos. NULL = sem SLA de primeira resposta.'
  AFTER `sla_minutos`;

-- 2. Adicionar campos SLA na tabela subcategorias (sobrescreve a categoria se definido)
ALTER TABLE `subcategorias`
  ADD COLUMN `sla_minutos` INT UNSIGNED DEFAULT NULL
  COMMENT 'SLA total em minutos. NULL = herda da categoria.'
  AFTER `descricao`,
  ADD COLUMN `sla_primeira_resposta_minutos` INT UNSIGNED DEFAULT NULL
  COMMENT 'SLA de primeira resposta em minutos. NULL = herda da categoria.'
  AFTER `sla_minutos`;

-- 3. Adicionar campos de primeira resposta na tabela ticket_sla
ALTER TABLE `ticket_sla`
  ADD COLUMN `sla_primeira_resposta_minutos` INT UNSIGNED DEFAULT NULL
  COMMENT 'SLA de primeira resposta copiado da categoria/subcategoria no momento da abertura'
  AFTER `sla_minutos`,
  ADD COLUMN `primeira_resposta_em` DATETIME DEFAULT NULL
  COMMENT 'Momento em que o suporte enviou a primeira resposta pública ao ticket'
  AFTER `sla_primeira_resposta_minutos`;
