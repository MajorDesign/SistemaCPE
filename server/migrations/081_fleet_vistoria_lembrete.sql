-- ============================================================
-- MIGRATION 081: Fluxo de vistoria + lembretes de devolucao
-- Data: 2026-07-02
-- Descricao: Fecha o buraco onde carro fica "disponivel" depois
-- de reserva vencida sem vistoria de retorno.
--
-- Mudancas:
--   1. Novo status intermedio no veiculo: 'aguardando_vistoria'
--      Ao devolver (condutor), veiculo NAO volta pra 'ativo'
--      direto — fica 'aguardando_vistoria' ate vistoriador aprovar.
--   2. 4 campos em fleet_checklists rastreiam envio de lembretes
--      pra garantir idempotencia (nao spam).
-- ============================================================

USE cpe_plus;

-- 1) Status intermedio "aguardando_vistoria"
ALTER TABLE fleet_vehicles
  MODIFY COLUMN status ENUM(
    'ativo',
    'em_viagem',
    'aguardando_vistoria',
    'manutencao',
    'revisao',
    'inativo'
  ) NOT NULL DEFAULT 'ativo';

-- 2) Rastreamento de lembretes (idempotencia por checklist)
ALTER TABLE fleet_checklists
  ADD COLUMN lembrete_1h_enviado_em         TIMESTAMP NULL DEFAULT NULL
    COMMENT 'quando o email "falta 1h" foi enviado',
  ADD COLUMN lembrete_vencimento_enviado_em TIMESTAMP NULL DEFAULT NULL
    COMMENT 'quando o email "vencido agora" foi enviado',
  ADD COLUMN lembrete_atrasado_ultimo_em    TIMESTAMP NULL DEFAULT NULL
    COMMENT 'ultimo email de "atrasado" (re-enviado a cada 3h)',
  ADD COLUMN escalada_frotas_enviada_em     TIMESTAMP NULL DEFAULT NULL
    COMMENT 'quando o RESPONSAVEL_GRUPO Frotas foi avisado (>=6h atraso)';

-- 3) Indice pra query do scheduler (busca frequente)
CREATE INDEX idx_checklists_status_datas
  ON fleet_checklists (status, data_retorno, horario_retorno);
