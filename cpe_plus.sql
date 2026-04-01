-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1:3306
-- Tempo de geração: 31/03/2026 às 14:25
-- Versão do servidor: 9.1.0
-- Versão do PHP: 8.3.14

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Banco de dados: `cpe_plus`
--

-- --------------------------------------------------------

--
-- Estrutura para tabela `categorias`
--

DROP TABLE IF EXISTS `categorias`;
CREATE TABLE IF NOT EXISTS `categorias` (
  `id` int UNSIGNED NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `nome` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descricao` text COLLATE utf8mb4_unicode_ci,
  `ativo` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_group_nome` (`group_id`,`nome`),
  KEY `idx_group_id` (`group_id`),
  KEY `idx_ativo` (`ativo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `departments`
--

DROP TABLE IF EXISTS `departments`;
CREATE TABLE IF NOT EXISTS `departments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `idx_name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `departments`
--

INSERT INTO `departments` (`id`, `name`, `description`, `created_at`, `updated_at`) VALUES
(1, 'TI', 'Departamento de Tecnologia da Informação', '2026-03-03 21:31:31', '2026-03-03 21:31:31'),
(2, 'RH', 'Departamento de Recursos Humanos', '2026-03-03 21:31:31', '2026-03-03 21:31:31'),
(3, 'Financeiro', 'Departamento Financeiro', '2026-03-03 21:31:31', '2026-03-03 21:31:31'),
(4, 'Administrativo', 'Departamento Administrativo', '2026-03-03 21:31:31', '2026-03-03 21:31:31');

-- --------------------------------------------------------

--
-- Estrutura para tabela `documents`
--

DROP TABLE IF EXISTS `documents`;
CREATE TABLE IF NOT EXISTS `documents` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `content` longtext,
  `visibility` enum('INTERNAL','SECTOR','PRIVATE','TI','RESTRICTED') NOT NULL DEFAULT 'INTERNAL',
  `sector` varchar(120) DEFAULT NULL,
  `owner_user_id` bigint NOT NULL,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_docs_owner` (`owner_user_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `groups`
--

DROP TABLE IF EXISTS `groups`;
CREATE TABLE IF NOT EXISTS `groups` (
  `id` int NOT NULL AUTO_INCREMENT,
  `department_id` int NOT NULL,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_group_per_dept` (`department_id`,`name`),
  KEY `idx_department` (`department_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `groups`
--

INSERT INTO `groups` (`id`, `department_id`, `name`, `description`, `created_at`, `updated_at`) VALUES
(2, 1, 'Suporte', 'Suporte da cpe', '2026-03-03 21:32:39', '2026-03-03 21:32:46');

-- --------------------------------------------------------

--
-- Estrutura para tabela `notificacoes`
--

DROP TABLE IF EXISTS `notificacoes`;
CREATE TABLE IF NOT EXISTS `notificacoes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ticket_id` int DEFAULT NULL,
  `usuario_id` int DEFAULT NULL,
  `mensagem` varchar(255) DEFAULT NULL,
  `tipo` varchar(50) DEFAULT NULL,
  `lido` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_usuario_lido` (`usuario_id`,`lido`) COMMENT 'Busca rápida de notificações não lidas por usuário',
  KEY `idx_usuario_criado` (`usuario_id`,`created_at`) COMMENT 'Timeline de notificações por data',
  KEY `idx_ticket_id` (`ticket_id`) COMMENT 'Buscar notificações de um ticket específico'
) ENGINE=MyISAM AUTO_INCREMENT=60 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Despejando dados para a tabela `notificacoes`
--

INSERT INTO `notificacoes` (`id`, `ticket_id`, `usuario_id`, `mensagem`, `tipo`, `lido`, `created_at`, `updated_at`) VALUES
(36, 8, 19, 'Comentário interno no ticket #SUP-2026-00005: isso aqui vou ter que ver mais tarde faça um comentario interno para me lembrar', 'comentario_interno', 1, '2026-03-30 19:07:39', '2026-03-30 19:07:51'),
(12, 7, 17, 'Ticket atribuído a 15', 'atribuido', 0, '2026-03-30 18:11:35', '2026-03-30 18:11:35'),
(34, 9, 19, 'Ticket atribuído a 15', 'atribuido', 1, '2026-03-30 18:53:49', '2026-03-30 18:54:01'),
(18, 8, 17, 'Novo ticket: \"novo teste de notificação tarde\" de Sistema', 'ticket_criado', 0, '2026-03-30 18:31:28', '2026-03-30 18:31:28'),
(9, 7, 17, 'Novo ticket: \"novo ticket de teste\" de Sistema', 'ticket_criado', 0, '2026-03-30 18:11:21', '2026-03-30 18:11:21'),
(35, 9, 19, 'Nova resposta no ticket #SUP-2026-00006: já esta sendo atendido', 'nova_resposta', 1, '2026-03-30 18:54:14', '2026-03-30 18:54:30'),
(33, 9, 17, 'Ticket atribuído a 15', 'atribuido', 0, '2026-03-30 18:53:49', '2026-03-30 18:53:49'),
(32, 9, 15, 'Ticket atribuído a 15', 'atribuido', 1, '2026-03-30 18:53:49', '2026-03-30 19:00:34'),
(31, 9, 19, 'Novo ticket: \"trocar mouse e teclado\" de Sistema', 'ticket_criado', 1, '2026-03-30 18:52:31', '2026-03-30 18:54:01'),
(21, 8, 17, 'Ticket atribuído a 15', 'atribuido', 0, '2026-03-30 18:31:53', '2026-03-30 18:31:53'),
(29, 9, 15, 'Novo ticket: \"trocar mouse e teclado\" de Sistema', 'ticket_criado', 1, '2026-03-30 18:52:31', '2026-03-30 18:53:17'),
(30, 9, 17, 'Novo ticket: \"trocar mouse e teclado\" de Sistema', 'ticket_criado', 0, '2026-03-30 18:52:31', '2026-03-30 18:52:31'),
(27, 8, 19, 'Comentário interno no ticket #SUP-2026-00005: interno', 'comentario_interno', 1, '2026-03-30 18:47:48', '2026-03-30 18:48:08'),
(28, 8, 20, 'Comentário interno no ticket #SUP-2026-00005: interno', 'comentario_interno', 0, '2026-03-30 18:47:48', '2026-03-30 18:47:48'),
(37, 8, 20, 'Comentário interno no ticket #SUP-2026-00005: isso aqui vou ter que ver mais tarde faça um comentario interno para me lembrar', 'comentario_interno', 0, '2026-03-30 19:07:39', '2026-03-30 19:07:39'),
(38, 8, 19, 'Status alterado para 3', 'status_alterado', 1, '2026-03-30 19:08:34', '2026-03-30 19:08:48'),
(39, 8, 20, 'Comentário interno no ticket #SUP-2026-00005: interno teste 2', 'comentario_interno', 0, '2026-03-30 19:38:52', '2026-03-30 19:38:52'),
(40, 8, 19, 'Nova resposta no ticket #SUP-2026-00005: resposta publica teste', 'nova_resposta', 1, '2026-03-30 19:39:17', '2026-03-30 19:39:21'),
(41, 8, 15, 'Nova resposta no ticket #SUP-2026-00005: teste recebido', 'nova_resposta', 1, '2026-03-30 19:39:40', '2026-03-30 19:39:49'),
(42, 10, 15, 'Novo ticket: \"teste de ticket id\" de Sistema', 'ticket_criado', 1, '2026-03-30 22:08:22', '2026-03-30 22:15:27'),
(43, 10, 17, 'Novo ticket: \"teste de ticket id\" de Sistema', 'ticket_criado', 0, '2026-03-30 22:08:22', '2026-03-30 22:08:22'),
(44, 10, 19, 'Novo ticket: \"teste de ticket id\" de Sistema', 'ticket_criado', 1, '2026-03-30 22:08:22', '2026-03-30 22:15:47'),
(45, 11, 15, 'Novo ticket: \"chamado\" de Sistema', 'ticket_criado', 1, '2026-03-30 22:14:09', '2026-03-30 22:15:30'),
(46, 11, 17, 'Novo ticket: \"chamado\" de Sistema', 'ticket_criado', 0, '2026-03-30 22:14:09', '2026-03-30 22:14:09'),
(47, 11, 19, 'Novo ticket: \"chamado\" de Sistema', 'ticket_criado', 1, '2026-03-30 22:14:09', '2026-03-30 22:15:47'),
(48, 11, 15, 'Ticket atribuído a 15', 'atribuido', 0, '2026-03-30 22:15:39', '2026-03-30 22:15:39'),
(49, 11, 17, 'Ticket atribuído a 15', 'atribuido', 0, '2026-03-30 22:15:39', '2026-03-30 22:15:39'),
(50, 11, 19, 'Ticket atribuído a 15', 'atribuido', 0, '2026-03-30 22:15:39', '2026-03-30 22:15:39'),
(51, 13, 15, 'Novo ticket: \"teste ticket alfa numerico\" de Sistema', 'ticket_criado', 0, '2026-03-30 22:46:33', '2026-03-30 22:46:33'),
(52, 13, 17, 'Novo ticket: \"teste ticket alfa numerico\" de Sistema', 'ticket_criado', 0, '2026-03-30 22:46:33', '2026-03-30 22:46:33'),
(53, 13, 19, 'Novo ticket: \"teste ticket alfa numerico\" de Sistema', 'ticket_criado', 0, '2026-03-30 22:46:33', '2026-03-30 22:46:33'),
(54, 14, 15, 'Novo ticket: \"novo teste de geração de ticket alfa\" de Sistema', 'ticket_criado', 0, '2026-03-30 22:47:18', '2026-03-30 22:47:18'),
(55, 14, 17, 'Novo ticket: \"novo teste de geração de ticket alfa\" de Sistema', 'ticket_criado', 0, '2026-03-30 22:47:18', '2026-03-30 22:47:18'),
(56, 14, 19, 'Novo ticket: \"novo teste de geração de ticket alfa\" de Sistema', 'ticket_criado', 0, '2026-03-30 22:47:18', '2026-03-30 22:47:18'),
(57, 15, 15, 'Novo ticket: \"segundo teste de ticket 2\" de Sistema', 'ticket_criado', 0, '2026-03-31 13:53:14', '2026-03-31 13:53:14'),
(58, 15, 17, 'Novo ticket: \"segundo teste de ticket 2\" de Sistema', 'ticket_criado', 0, '2026-03-31 13:53:14', '2026-03-31 13:53:14'),
(59, 15, 19, 'Novo ticket: \"segundo teste de ticket 2\" de Sistema', 'ticket_criado', 0, '2026-03-31 13:53:14', '2026-03-31 13:53:14');

-- --------------------------------------------------------

--
-- Estrutura para tabela `passwords`
--

DROP TABLE IF EXISTS `passwords`;
CREATE TABLE IF NOT EXISTS `passwords` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `client` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `link` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observation` text COLLATE utf8mb4_unicode_ci,
  `group_id` int DEFAULT NULL,
  `is_public` tinyint(1) DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_exclusive` tinyint(1) DEFAULT '0',
  `allowed_group_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_group_id` (`group_id`),
  KEY `idx_allowed_group` (`allowed_group_id`),
  KEY `idx_is_exclusive` (`is_exclusive`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `passwords`
--

INSERT INTO `passwords` (`id`, `user_id`, `client`, `email`, `description`, `password`, `link`, `observation`, `group_id`, `is_public`, `created_at`, `updated_at`, `is_exclusive`, `allowed_group_id`) VALUES
(1, 1, 'tese', 'admin@cpe.com.br', 'teste', '22223333', 'https://github.com/cpeinfra-cmyk/cpenavigator', 'teste22', NULL, 0, '2026-03-07 07:17:57', '2026-03-07 07:17:57', 0, NULL),
(2, 1, 'teste 55', 'admin@cpe.com.br', 'teste 44', 'd3d5t7gas1436', 'https://github.com/cpeinfra-cmyk/cpenavigator', '3d3t', NULL, 0, '2026-03-07 16:27:31', '2026-03-07 16:27:31', 0, NULL),
(4, 1, 'Jon', 'admin@cpe.com.br', 'teste jon', 'jon123', 'https://github.com/login/oauth/authorize', 'teste jon', NULL, 0, '2026-03-10 14:57:10', '2026-03-10 14:57:10', 0, NULL);

-- --------------------------------------------------------

--
-- Estrutura para tabela `password_groups`
--

DROP TABLE IF EXISTS `password_groups`;
CREATE TABLE IF NOT EXISTS `password_groups` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `user_group_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `password_groups`
--

INSERT INTO `password_groups` (`id`, `user_id`, `name`, `created_at`, `updated_at`, `user_group_id`) VALUES
(1, 0, 'Suporte', '2026-03-18 15:34:25', '2026-03-18 15:34:25', NULL),
(2, 0, 'Financeiro', '2026-03-18 19:20:43', '2026-03-18 19:20:43', NULL),
(3, 0, 'Assistencia', '2026-03-25 13:35:51', '2026-03-25 13:35:51', NULL),
(4, 0, 'faturamento', '2026-03-30 16:15:10', '2026-03-30 16:15:10', NULL);

-- --------------------------------------------------------

--
-- Estrutura para tabela `subcategorias`
--

DROP TABLE IF EXISTS `subcategorias`;
CREATE TABLE IF NOT EXISTS `subcategorias` (
  `id` int UNSIGNED NOT NULL AUTO_INCREMENT,
  `categoria_id` int UNSIGNED NOT NULL,
  `nome` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descricao` text COLLATE utf8mb4_unicode_ci,
  `ativo` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_categoria_nome` (`categoria_id`,`nome`),
  KEY `idx_categoria_id` (`categoria_id`),
  KEY `idx_ativo` (`ativo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `tickets`
--

DROP TABLE IF EXISTS `tickets`;
CREATE TABLE IF NOT EXISTS `tickets` (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `numero` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_alfanumerica` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `solicitante_id` bigint NOT NULL,
  `responsavel_id` bigint DEFAULT NULL,
  `group_id` int NOT NULL,
  `categoria_id` int UNSIGNED DEFAULT NULL,
  `subcategoria_id` int UNSIGNED DEFAULT NULL,
  `status_id` int UNSIGNED NOT NULL,
  `prioridade_id` int UNSIGNED NOT NULL,
  `assunto` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descricao_inicial` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `origem` enum('portal','email','whatsapp','telefone','api','interno') COLLATE utf8mb4_unicode_ci DEFAULT 'portal',
  `sla_primeira_resposta_em` datetime DEFAULT NULL,
  `sla_resolucao_em` datetime DEFAULT NULL,
  `primeira_resposta_em` datetime DEFAULT NULL,
  `resolvido_em` datetime DEFAULT NULL,
  `fechado_em` datetime DEFAULT NULL,
  `ultimo_evento_em` datetime DEFAULT CURRENT_TIMESTAMP,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `numero` (`numero`),
  UNIQUE KEY `uk_numero` (`numero`),
  UNIQUE KEY `id_alfanumerica` (`id_alfanumerica`),
  KEY `idx_solicitante_id` (`solicitante_id`),
  KEY `idx_responsavel_id` (`responsavel_id`),
  KEY `idx_group_id` (`group_id`),
  KEY `idx_categoria_id` (`categoria_id`),
  KEY `idx_subcategoria_id` (`subcategoria_id`),
  KEY `idx_status_id` (`status_id`),
  KEY `idx_prioridade_id` (`prioridade_id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_ultimo_evento_em` (`ultimo_evento_em`),
  KEY `idx_origem` (`origem`),
  KEY `idx_comp_group_status` (`group_id`,`status_id`,`created_at`),
  KEY `idx_comp_responsavel_status` (`responsavel_id`,`status_id`,`created_at`),
  KEY `idx_comp_status_criacao` (`status_id`,`created_at`),
  KEY `idx_id_alfanumerica` (`id_alfanumerica`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `tickets`
--

INSERT INTO `tickets` (`id`, `numero`, `id_alfanumerica`, `solicitante_id`, `responsavel_id`, `group_id`, `categoria_id`, `subcategoria_id`, `status_id`, `prioridade_id`, `assunto`, `descricao_inicial`, `origem`, `sla_primeira_resposta_em`, `sla_resolucao_em`, `primeira_resposta_em`, `resolvido_em`, `fechado_em`, `ultimo_evento_em`, `created_at`, `updated_at`) VALUES
(15, 'SUP-2026-00001', NULL, 15, NULL, 1, NULL, NULL, 1, 2, 'segundo teste de ticket 2', 'teste numercao', '', NULL, NULL, NULL, NULL, NULL, '2026-03-31 10:53:14', '2026-03-31 13:53:14', '2026-03-31 13:53:14');

-- --------------------------------------------------------

--
-- Estrutura para tabela `ticket_anexos`
--

DROP TABLE IF EXISTS `ticket_anexos`;
CREATE TABLE IF NOT EXISTS `ticket_anexos` (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `ticket_id` bigint UNSIGNED NOT NULL,
  `interacao_id` bigint UNSIGNED DEFAULT NULL,
  `nome_original` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `caminho_arquivo` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `mime_type` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tamanho_bytes` bigint UNSIGNED DEFAULT NULL,
  `enviado_por` bigint NOT NULL,
  `ativo` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_ticket_id` (`ticket_id`),
  KEY `idx_interacao_id` (`interacao_id`),
  KEY `idx_enviado_por` (`enviado_por`),
  KEY `idx_ativo` (`ativo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `ticket_interacoes`
--

DROP TABLE IF EXISTS `ticket_interacoes`;
CREATE TABLE IF NOT EXISTS `ticket_interacoes` (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `ticket_id` bigint UNSIGNED NOT NULL,
  `usuario_id` bigint NOT NULL,
  `tipo` enum('mensagem','nota_interna','alteracao_status','atribuicao','sistema') COLLATE utf8mb4_unicode_ci DEFAULT 'mensagem',
  `publico` tinyint(1) DEFAULT '1',
  `mensagem` longtext COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_ticket_id` (`ticket_id`),
  KEY `idx_usuario_id` (`usuario_id`),
  KEY `idx_tipo` (`tipo`),
  KEY `idx_publico` (`publico`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_comp_ticket_created` (`ticket_id`,`created_at`),
  KEY `idx_ticket_publico_criacao` (`ticket_id`,`publico`,`created_at`) COMMENT 'Carregar interações públicas/privadas de um ticket'
) ENGINE=InnoDB AUTO_INCREMENT=42 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `ticket_prioridades`
--

DROP TABLE IF EXISTS `ticket_prioridades`;
CREATE TABLE IF NOT EXISTS `ticket_prioridades` (
  `id` int UNSIGNED NOT NULL AUTO_INCREMENT,
  `nome` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nivel` tinyint NOT NULL,
  `descricao` text COLLATE utf8mb4_unicode_ci,
  `cor_hex` varchar(7) COLLATE utf8mb4_unicode_ci DEFAULT '#667eea',
  `sla_horas` int DEFAULT '48',
  `ativo` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nome` (`nome`),
  UNIQUE KEY `nivel` (`nivel`),
  KEY `idx_nivel` (`nivel`),
  KEY `idx_ativo` (`ativo`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `ticket_prioridades`
--

INSERT INTO `ticket_prioridades` (`id`, `nome`, `nivel`, `descricao`, `cor_hex`, `sla_horas`, `ativo`, `created_at`, `updated_at`) VALUES
(1, 'Baixa', 1, 'Prioridade baixa', '#17a2b8', 48, 1, '2026-03-20 17:30:17', '2026-03-20 17:30:17'),
(2, 'Média', 2, 'Prioridade média', '#ffc107', 48, 1, '2026-03-20 17:30:17', '2026-03-20 17:30:17'),
(3, 'Alta', 3, 'Prioridade alta', '#fd7e14', 48, 1, '2026-03-20 17:30:17', '2026-03-20 17:30:17'),
(4, 'Crítica', 4, 'Prioridade crítica', '#dc3545', 48, 1, '2026-03-20 17:30:17', '2026-03-20 17:30:17');

-- --------------------------------------------------------

--
-- Estrutura para tabela `ticket_status`
--

DROP TABLE IF EXISTS `ticket_status`;
CREATE TABLE IF NOT EXISTS `ticket_status` (
  `id` int UNSIGNED NOT NULL AUTO_INCREMENT,
  `nome` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descricao` text COLLATE utf8mb4_unicode_ci,
  `ordem` tinyint NOT NULL DEFAULT '0',
  `finalizador` tinyint(1) DEFAULT '0',
  `cor_hex` varchar(7) COLLATE utf8mb4_unicode_ci DEFAULT '#667eea',
  `ativo` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nome` (`nome`),
  KEY `idx_ordem` (`ordem`),
  KEY `idx_finalizador` (`finalizador`),
  KEY `idx_ativo` (`ativo`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `ticket_status`
--

INSERT INTO `ticket_status` (`id`, `nome`, `descricao`, `ordem`, `finalizador`, `cor_hex`, `ativo`, `created_at`, `updated_at`) VALUES
(1, 'Aberto', 'Ticket recém aberto', 0, 0, '#667eea', 1, '2026-03-20 17:24:13', '2026-03-20 17:24:13'),
(2, 'Em Andamento', 'Ticket sendo atendido', 0, 0, '#667eea', 1, '2026-03-20 17:24:13', '2026-03-20 17:24:13'),
(3, 'Aguardando', 'Aguardando resposta do usuário', 0, 0, '#667eea', 1, '2026-03-20 17:24:13', '2026-03-20 17:24:13'),
(4, 'Resolvido', 'Problema resolvido', 0, 0, '#667eea', 1, '2026-03-20 17:24:13', '2026-03-20 17:24:13'),
(5, 'Fechado', 'Ticket encerrado', 0, 0, '#667eea', 1, '2026-03-20 17:24:13', '2026-03-20 17:24:13');

-- --------------------------------------------------------

--
-- Estrutura para tabela `users`
--

DROP TABLE IF EXISTS `users`;
CREATE TABLE IF NOT EXISTS `users` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(120) NOT NULL,
  `email` varchar(190) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` enum('USER','TI','ADMIN') NOT NULL DEFAULT 'USER',
  `sector` varchar(120) DEFAULT NULL,
  `unit` varchar(120) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `username` varchar(50) DEFAULT NULL,
  `department_id` int DEFAULT NULL,
  `group_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `username` (`username`),
  KEY `idx_department` (`department_id`),
  KEY `idx_group` (`group_id`)
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Despejando dados para a tabela `users`
--

INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `role`, `sector`, `unit`, `is_active`, `created_at`, `username`, `department_id`, `group_id`) VALUES
(15, 'Administrador', 'admin@cpe.com.br', '$2b$12$cUzgsKcnlFpM4RLi4s6ice887vhB4RqDprqSCAeeTLpCiyhnjLkZ.', 'ADMIN', NULL, NULL, 1, '2026-03-18 21:01:36', 'admin', NULL, 1),
(17, 'Manager System', 'manager@cpe.com.br', '$2b$12$e5owWqUGPxvGMQdM3dUVDe2O0k0vqCqRVJr.qiHqnINNk.G9K2i3O', '', NULL, NULL, 1, '2026-03-18 21:01:36', 'manager', NULL, 1),
(19, 'jonathan', 'jonathan2@cpe.com.br', '$2b$12$gAsoH/SsdblwHN.kd9djQeFMXb3Kep0q8rUbfe0kNSYbPTlw.X2Xa', 'USER', NULL, NULL, 1, '2026-03-18 21:43:48', 'jonathan.lopes2', NULL, 1),
(20, 'fernanda', 'fernandateste@cpe.com.br', '$2b$12$14PTC6nIsDE1TBi9/tOGZuDT2WmTMAB3R6mdqXCZ6mMGnahe8k4Xe', 'ADMIN', NULL, NULL, 1, '2026-03-18 22:19:27', 'fernanda.teste', NULL, 3);

-- --------------------------------------------------------

--
-- Estrutura stand-in para view `vw_historico_notificacoes`
-- (Veja abaixo para a visão atual)
--
DROP VIEW IF EXISTS `vw_historico_notificacoes`;
CREATE TABLE IF NOT EXISTS `vw_historico_notificacoes` (
`id` int
,`ticket_id` int
,`ticket_numero` varchar(20)
,`ticket_assunto` varchar(255)
,`usuario_id` int
,`usuario_nome` varchar(120)
,`mensagem` varchar(255)
,`tipo` varchar(50)
,`lido` tinyint(1)
,`created_at` timestamp
,`updated_at` timestamp
);

-- --------------------------------------------------------

--
-- Estrutura stand-in para view `vw_notificacoes_nao_lidas`
-- (Veja abaixo para a visão atual)
--
DROP VIEW IF EXISTS `vw_notificacoes_nao_lidas`;
CREATE TABLE IF NOT EXISTS `vw_notificacoes_nao_lidas` (
`usuario_id` bigint
,`usuario_nome` varchar(120)
,`total_nao_lidas` bigint
,`atribuidos` bigint
,`respondidos` bigint
,`transferidos` bigint
,`finalizados` bigint
,`ultima_notificacao` timestamp
);

-- --------------------------------------------------------

--
-- Estrutura para view `vw_historico_notificacoes`
--
DROP TABLE IF EXISTS `vw_historico_notificacoes`;

DROP VIEW IF EXISTS `vw_historico_notificacoes`;
CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vw_historico_notificacoes`  AS SELECT `n`.`id` AS `id`, `n`.`ticket_id` AS `ticket_id`, `t`.`numero` AS `ticket_numero`, `t`.`assunto` AS `ticket_assunto`, `n`.`usuario_id` AS `usuario_id`, `u`.`name` AS `usuario_nome`, `n`.`mensagem` AS `mensagem`, `n`.`tipo` AS `tipo`, `n`.`lido` AS `lido`, `n`.`created_at` AS `created_at`, `n`.`updated_at` AS `updated_at` FROM ((`notificacoes` `n` join `tickets` `t` on((`n`.`ticket_id` = `t`.`id`))) join `users` `u` on((`n`.`usuario_id` = `u`.`id`))) ORDER BY `n`.`created_at` DESC ;

-- --------------------------------------------------------

--
-- Estrutura para view `vw_notificacoes_nao_lidas`
--
DROP TABLE IF EXISTS `vw_notificacoes_nao_lidas`;

DROP VIEW IF EXISTS `vw_notificacoes_nao_lidas`;
CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vw_notificacoes_nao_lidas`  AS SELECT `u`.`id` AS `usuario_id`, `u`.`name` AS `usuario_nome`, count(`n`.`id`) AS `total_nao_lidas`, count((case when (`n`.`tipo` = 'atribuido') then 1 end)) AS `atribuidos`, count((case when (`n`.`tipo` = 'respondido') then 1 end)) AS `respondidos`, count((case when (`n`.`tipo` = 'transferido') then 1 end)) AS `transferidos`, count((case when (`n`.`tipo` = 'finalizado') then 1 end)) AS `finalizados`, max(`n`.`created_at`) AS `ultima_notificacao` FROM (`users` `u` left join `notificacoes` `n` on(((`u`.`id` = `n`.`usuario_id`) and (`n`.`lido` = false)))) GROUP BY `u`.`id`, `u`.`name` ORDER BY `total_nao_lidas` DESC ;

--
-- Restrições para tabelas despejadas
--

--
-- Restrições para tabelas `categorias`
--
ALTER TABLE `categorias`
  ADD CONSTRAINT `fk_categorias_group` FOREIGN KEY (`group_id`) REFERENCES `password_groups` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `groups`
--
ALTER TABLE `groups`
  ADD CONSTRAINT `groups_ibfk_1` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `subcategorias`
--
ALTER TABLE `subcategorias`
  ADD CONSTRAINT `fk_subcategorias_categoria` FOREIGN KEY (`categoria_id`) REFERENCES `categorias` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `tickets`
--
ALTER TABLE `tickets`
  ADD CONSTRAINT `fk_tickets_categoria` FOREIGN KEY (`categoria_id`) REFERENCES `categorias` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `fk_tickets_group` FOREIGN KEY (`group_id`) REFERENCES `password_groups` (`id`) ON DELETE RESTRICT,
  ADD CONSTRAINT `fk_tickets_prioridade` FOREIGN KEY (`prioridade_id`) REFERENCES `ticket_prioridades` (`id`) ON DELETE RESTRICT,
  ADD CONSTRAINT `fk_tickets_responsavel` FOREIGN KEY (`responsavel_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `fk_tickets_solicitante` FOREIGN KEY (`solicitante_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT,
  ADD CONSTRAINT `fk_tickets_status` FOREIGN KEY (`status_id`) REFERENCES `ticket_status` (`id`) ON DELETE RESTRICT,
  ADD CONSTRAINT `fk_tickets_subcategoria` FOREIGN KEY (`subcategoria_id`) REFERENCES `subcategorias` (`id`) ON DELETE SET NULL;

--
-- Restrições para tabelas `ticket_anexos`
--
ALTER TABLE `ticket_anexos`
  ADD CONSTRAINT `fk_anexos_interacao` FOREIGN KEY (`interacao_id`) REFERENCES `ticket_interacoes` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `fk_anexos_ticket` FOREIGN KEY (`ticket_id`) REFERENCES `tickets` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_anexos_usuario` FOREIGN KEY (`enviado_por`) REFERENCES `users` (`id`) ON DELETE RESTRICT;

--
-- Restrições para tabelas `ticket_interacoes`
--
ALTER TABLE `ticket_interacoes`
  ADD CONSTRAINT `fk_interacoes_ticket` FOREIGN KEY (`ticket_id`) REFERENCES `tickets` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_interacoes_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
