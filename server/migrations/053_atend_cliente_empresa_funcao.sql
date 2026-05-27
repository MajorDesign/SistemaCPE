-- =====================================================================
-- Migration 053 - Empresa e funcao do cliente no agendamento
-- =====================================================================
-- Pedido do usuario: no formulario publico, capturar tambem empresa do
-- cliente e funcao dele na empresa. Esses dados vao alimentar a base
-- de clientes (Menu "Clientes" no equipe-suporte).
--
-- A base de clientes e DERIVADA dos agendamentos (sem tabela propria):
-- deduplicada por cliente_email, com historico completo.
-- =====================================================================

ALTER TABLE `atend_agendamentos`
  ADD COLUMN `cliente_empresa` VARCHAR(150) NULL
      COMMENT 'Nome da empresa onde o cliente trabalha'
      AFTER `cliente_telefone`,
  ADD COLUMN `cliente_funcao` VARCHAR(120) NULL
      COMMENT 'Funcao/cargo do cliente na empresa'
      AFTER `cliente_empresa`,
  ADD KEY `idx_atend_cliente_email` (`cliente_email`);
