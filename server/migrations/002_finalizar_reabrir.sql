-- Migration 002: reopen_count + novos tipos de interação
-- Executar uma vez. Idempotente via IF NOT EXISTS / IF NOT EXISTS emulado.

-- 1. Adiciona reopen_count na tabela tickets
ALTER TABLE tickets
  ADD COLUMN IF NOT EXISTS reopen_count TINYINT UNSIGNED NOT NULL DEFAULT 0
  COMMENT 'Quantas vezes o chamado foi reaberto pelo solicitante (máx. 2)';

-- 2. Adiciona os novos valores 'reabertura' e 'resolucao' ao enum de tipo
--    MySQL exige reescrita completa do MODIFY COLUMN para enums.
ALTER TABLE ticket_interacoes MODIFY COLUMN tipo
  ENUM(
    'mensagem',
    'nota_interna',
    'alteracao_status',
    'atribuicao',
    'sistema',
    'encaminhamento',
    'devolucao',
    'sla_iniciado',
    'sla_pausado',
    'sla_retomado',
    'sla_concluido',
    'sla_estourado',
    'reabertura',
    'resolucao'
  ) COLLATE utf8mb4_unicode_ci DEFAULT 'mensagem';
