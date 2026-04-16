-- ============================================================
-- MÓDULO DE FROTAS - Migration 006
-- Data: 2026-04-15
-- Descrição: Novo fluxo de checklist
--   - Condutor assina saída (aguardando_vistoria)
--   - Vistoriador distinto aprova saída (aprovado)
--   - Retorno exclusivo do vistoriador
--   - Retorno com avaria deixa veículo em manutencao
-- ============================================================

USE cpe_plus;

-- Ampliar ENUM de status do checklist
ALTER TABLE fleet_checklists
  MODIFY COLUMN status ENUM(
    'aguardando_vistoria',
    'aguardando_aprovacao',
    'aprovado',
    'em_viagem',
    'retornado',
    'retornado_com_avaria',
    'cancelado'
  ) DEFAULT 'aguardando_vistoria';

-- Adicionar observações do retorno e assinatura do vistoriador de retorno
ALTER TABLE fleet_checklists
  ADD COLUMN IF NOT EXISTS retorno_obs TEXT COMMENT 'Observacoes do vistoriador no retorno',
  ADD COLUMN IF NOT EXISTS assinatura_vistoriador_retorno MEDIUMTEXT COMMENT 'Assinatura do vistoriador no retorno';

-- Distinguir problemas da saída vs retorno
ALTER TABLE fleet_checklist_problems
  ADD COLUMN IF NOT EXISTS fase ENUM('saida','retorno') DEFAULT 'saida' COMMENT 'Em qual fase o problema foi detectado';
