-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1:3306
-- Tempo de geração: 08/04/2026 às 16:18
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
  `sla_minutos` int UNSIGNED DEFAULT NULL COMMENT 'SLA em minutos. NULL = sem SLA definido.',
  `ativo` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_group_nome` (`group_id`,`nome`),
  KEY `idx_group_id` (`group_id`),
  KEY `idx_ativo` (`ativo`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `categorias`
--

INSERT INTO `categorias` (`id`, `group_id`, `nome`, `descricao`, `sla_minutos`, `ativo`, `created_at`, `updated_at`) VALUES
(1, 5, 'Notas a cancelar', 'categoria destinado a notas a cancelar', NULL, 1, '2026-04-08 12:45:57', '2026-04-08 12:45:57'),
(2, 5, 'notas ja emitida', 'teste emição', 10, 1, '2026-04-08 13:19:44', '2026-04-08 13:22:25');

-- --------------------------------------------------------

--
-- Estrutura para tabela `cpe_grupo`
--

DROP TABLE IF EXISTS `cpe_grupo`;
CREATE TABLE IF NOT EXISTS `cpe_grupo` (
  `id` int NOT NULL AUTO_INCREMENT,
  `department_id` int NOT NULL,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_group_per_dept` (`department_id`,`name`),
  KEY `idx_department` (`department_id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `cpe_grupo`
--

INSERT INTO `cpe_grupo` (`id`, `department_id`, `name`, `description`, `created_at`, `updated_at`) VALUES
(1, 1, 'Suporte', 'Suporte da CPE', '2026-04-01 13:08:58', '2026-04-01 13:08:58'),
(3, 2, 'assistencia', 'Assistência Técnica da CPE', '2026-04-01 13:08:58', '2026-04-07 17:38:25'),
(4, 3, 'Financeiro', 'Departamento Financeiro', '2026-04-01 13:08:58', '2026-04-01 13:08:58'),
(5, 3, 'Faturamento', 'Setor de Faturamento', '2026-04-01 13:08:58', '2026-04-01 13:08:58'),
(7, 1, 'teste', NULL, '2026-04-07 17:44:09', '2026-04-07 17:44:09');

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
) ENGINE=MyISAM AUTO_INCREMENT=108 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Despejando dados para a tabela `notificacoes`
--

INSERT INTO `notificacoes` (`id`, `ticket_id`, `usuario_id`, `mensagem`, `tipo`, `lido`, `created_at`, `updated_at`) VALUES
(12, 7, 17, 'Ticket atribuído a 15', 'atribuido', 0, '2026-03-30 18:11:35', '2026-03-30 18:11:35'),
(18, 8, 17, 'Novo ticket: \"novo teste de notificação tarde\" de Sistema', 'ticket_criado', 0, '2026-03-30 18:31:28', '2026-03-30 18:31:28'),
(9, 7, 17, 'Novo ticket: \"novo ticket de teste\" de Sistema', 'ticket_criado', 0, '2026-03-30 18:11:21', '2026-03-30 18:11:21'),
(33, 9, 17, 'Ticket atribuído a 15', 'atribuido', 0, '2026-03-30 18:53:49', '2026-03-30 18:53:49'),
(79, 19, 17, 'Novo ticket: \"segundo teste de ticket 2\" de Sistema', 'ticket_criado', 0, '2026-03-31 22:14:58', '2026-03-31 22:14:58'),
(21, 8, 17, 'Ticket atribuído a 15', 'atribuido', 0, '2026-03-30 18:31:53', '2026-03-30 18:31:53'),
(101, 21, 20, 'Seu chamado foi assumido por Usuário #23', 'ticket_atribuido', 1, '2026-04-07 19:19:25', '2026-04-07 19:20:08'),
(30, 9, 17, 'Novo ticket: \"trocar mouse e teclado\" de Sistema', 'ticket_criado', 0, '2026-03-30 18:52:31', '2026-03-30 18:52:31'),
(105, 24, 20, 'Status alterado para 3', 'status_alterado', 1, '2026-04-08 14:16:26', '2026-04-08 14:46:05'),
(106, 22, 20, 'Seu chamado foi assumido por Usuário #15', 'ticket_atribuido', 1, '2026-04-08 14:53:18', '2026-04-08 14:53:32'),
(102, 21, 23, 'Nova resposta no ticket #SUP-2026-00006: camila atende ok', 'nova_resposta', 1, '2026-04-07 19:20:36', '2026-04-07 19:20:55'),
(99, 21, 20, 'Nova resposta no ticket #SUP-2026-00006: teste 222', 'nova_resposta', 1, '2026-04-07 18:51:45', '2026-04-07 19:20:02'),
(100, 21, 20, 'Ticket encaminhado para \'assistencia\' por Administrador: ', 'ticket_encaminhado', 1, '2026-04-07 18:59:43', '2026-04-07 19:20:02'),
(96, 21, 20, 'Nova resposta no ticket #SUP-2026-00006: teste 222', 'nova_resposta', 1, '2026-04-07 18:28:42', '2026-04-07 18:28:49'),
(97, 21, 17, 'Ticket atribuído a 15', 'atribuido', 0, '2026-04-07 18:51:27', '2026-04-07 18:51:27'),
(98, 21, 19, 'Ticket atribuído a 15', 'atribuido', 0, '2026-04-07 18:51:27', '2026-04-07 18:51:27'),
(95, 21, 19, 'Novo ticket: \"segundo teste de ticket3\" de Sistema', 'ticket_criado', 0, '2026-04-07 18:23:18', '2026-04-07 18:23:18'),
(43, 10, 17, 'Novo ticket: \"teste de ticket id\" de Sistema', 'ticket_criado', 0, '2026-03-30 22:08:22', '2026-03-30 22:08:22'),
(92, 20, 20, 'Nova resposta no ticket #ASS-2026-00001: resposta teste', 'nova_resposta', 1, '2026-04-07 17:56:42', '2026-04-07 17:57:25'),
(93, 20, 20, 'Nova resposta no ticket #ASS-2026-00001: ok ok ok', 'nova_resposta', 1, '2026-04-07 17:57:39', '2026-04-07 17:57:47'),
(46, 11, 17, 'Novo ticket: \"chamado\" de Sistema', 'ticket_criado', 0, '2026-03-30 22:14:09', '2026-03-30 22:14:09'),
(82, 19, 17, 'Ticket atribuído a 15', 'atribuido', 0, '2026-03-31 22:15:27', '2026-03-31 22:15:27'),
(49, 11, 17, 'Ticket atribuído a 15', 'atribuido', 0, '2026-03-30 22:15:39', '2026-03-30 22:15:39'),
(104, 24, 20, 'Seu chamado foi assumido por Usuário #15', 'ticket_atribuido', 1, '2026-04-08 13:23:08', '2026-04-08 13:23:24'),
(52, 13, 17, 'Novo ticket: \"teste ticket alfa numerico\" de Sistema', 'ticket_criado', 0, '2026-03-30 22:46:33', '2026-03-30 22:46:33'),
(70, 18, 17, 'Ticket atribuído a 19', 'atribuido', 0, '2026-03-31 20:36:31', '2026-03-31 20:36:31'),
(55, 14, 17, 'Novo ticket: \"novo teste de geração de ticket alfa\" de Sistema', 'ticket_criado', 0, '2026-03-30 22:47:18', '2026-03-30 22:47:18'),
(88, 19, 15, 'Nova resposta no ticket #SUP-2026-00005: okok', 'nova_resposta', 1, '2026-04-01 17:44:48', '2026-04-01 17:44:53'),
(103, 23, 20, 'Seu chamado foi assumido por Usuário #15', 'ticket_atribuido', 1, '2026-04-08 13:20:27', '2026-04-08 13:21:18'),
(58, 15, 17, 'Novo ticket: \"segundo teste de ticket 2\" de Sistema', 'ticket_criado', 0, '2026-03-31 13:53:14', '2026-03-31 13:53:14'),
(94, 21, 17, 'Novo ticket: \"segundo teste de ticket3\" de Sistema', 'ticket_criado', 0, '2026-04-07 18:23:18', '2026-04-07 18:23:18'),
(61, 16, 17, 'Novo ticket: \"Teste final do sistema\" de Sistema', 'ticket_criado', 0, '2026-03-31 14:34:45', '2026-03-31 14:34:45'),
(87, 19, 19, 'Nova resposta no ticket #SUP-2026-00005: 23456', 'nova_resposta', 1, '2026-04-01 17:44:35', '2026-04-01 17:44:44'),
(67, 18, 17, 'Novo ticket: \"novo teste 1234\" de Sistema', 'ticket_criado', 0, '2026-03-31 20:36:13', '2026-03-31 20:36:13'),
(64, 17, 17, 'Novo ticket: \"tests 1111\" de Sistema', 'ticket_criado', 0, '2026-03-31 15:20:32', '2026-03-31 15:20:32'),
(107, 23, 20, 'Seu chamado foi assumido por Usuário #15', 'ticket_atribuido', 1, '2026-04-08 14:53:24', '2026-04-08 14:53:34');

-- --------------------------------------------------------

--
-- Estrutura para tabela `page_permissions`
--

DROP TABLE IF EXISTS `page_permissions`;
CREATE TABLE IF NOT EXISTS `page_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `page_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Nome da página (ex: CHAT, USERS)',
  `allowed_roles` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Roles separados por vírgula (ex: ADMIN,TI)',
  `updated_by` int DEFAULT NULL COMMENT 'ID do admin que alterou',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_page_name` (`page_name`),
  KEY `idx_page_name` (`page_name`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `page_permissions`
--

INSERT INTO `page_permissions` (`id`, `page_name`, `allowed_roles`, `updated_by`, `updated_at`) VALUES
(1, 'DASHBOARD', 'USER,RESPONSAVEL_GRUPO,ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(2, 'TICKETS', 'USER,RESPONSAVEL_GRUPO,ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(3, 'CHAT', 'USER,RESPONSAVEL_GRUPO,ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(4, 'TASKS', 'USER,RESPONSAVEL_GRUPO,ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(5, 'PROJECTS', 'USER,RESPONSAVEL_GRUPO,ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(6, 'KNOWLEDGE_BASE', 'USER,RESPONSAVEL_GRUPO,ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(7, 'DOWNLOAD_AGENTS', 'USER,RESPONSAVEL_GRUPO,ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(8, 'GROUPS', 'ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(9, 'REGISTRATIONS', 'ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(10, 'REPORTS', 'ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(11, 'BILLING', 'ADMIN,MANAGER', NULL, '2026-04-06 22:28:35'),
(12, 'USERS', 'ADMIN,TI', NULL, '2026-04-06 22:28:35'),
(13, 'INVENTORY', 'ADMIN,TI', NULL, '2026-04-06 22:28:35'),
(14, 'PASSWORD_VAULT', 'ADMIN,TI', NULL, '2026-04-06 22:28:35'),
(15, 'SETTINGS', 'ADMIN', NULL, '2026-04-06 22:28:35'),
(16, 'PERMISSIONS', 'ADMIN', NULL, '2026-04-06 22:28:35');

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
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `subcategorias`
--

INSERT INTO `subcategorias` (`id`, `categoria_id`, `nome`, `descricao`, `ativo`, `created_at`, `updated_at`) VALUES
(1, 1, 'notas já canceladas', 'notas que já foram canceladas', 1, '2026-04-08 12:46:25', '2026-04-08 12:46:25');

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
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `tickets`
--

INSERT INTO `tickets` (`id`, `numero`, `id_alfanumerica`, `solicitante_id`, `responsavel_id`, `group_id`, `categoria_id`, `subcategoria_id`, `status_id`, `prioridade_id`, `assunto`, `descricao_inicial`, `origem`, `sla_primeira_resposta_em`, `sla_resolucao_em`, `primeira_resposta_em`, `resolvido_em`, `fechado_em`, `ultimo_evento_em`, `created_at`, `updated_at`) VALUES
(15, 'SUP-2026-00001', NULL, 15, NULL, 1, NULL, NULL, 1, 2, 'segundo teste de ticket 2', 'teste numercao', '', NULL, NULL, NULL, NULL, NULL, '2026-03-31 10:53:14', '2026-03-31 13:53:14', '2026-03-31 13:53:14'),
(16, 'SUP-2026-00002', NULL, 15, NULL, 1, NULL, NULL, 1, 2, 'Teste final do sistema', 'Deve gerar ID alfanumérica', 'portal', NULL, NULL, NULL, NULL, NULL, '2026-03-31 11:34:45', '2026-03-31 14:34:45', '2026-03-31 14:34:45'),
(17, 'SUP-2026-00003', NULL, 15, NULL, 1, NULL, NULL, 1, 2, 'tests 1111', 'tetset1111', '', NULL, NULL, NULL, NULL, NULL, '2026-03-31 12:20:32', '2026-03-31 15:20:32', '2026-03-31 15:20:32'),
(18, 'SUP-2026-00004', 'SU0018N6T4', 15, 19, 1, NULL, NULL, 1, 2, 'novo teste 1234', 'teste 1235456', '', NULL, NULL, NULL, NULL, NULL, '2026-03-31 17:36:13', '2026-03-31 20:36:13', '2026-03-31 20:36:30'),
(19, 'SUP-2026-00005', 'SU0019N6T0', 19, 15, 1, NULL, NULL, 1, 1, 'segundo teste de ticket 2', 'teste 222', '', NULL, NULL, NULL, NULL, NULL, '2026-03-31 19:14:58', '2026-03-31 22:14:58', '2026-03-31 22:15:27'),
(21, 'SUP-2026-00006', 'SU0021N6T7', 20, 23, 3, NULL, NULL, 2, 2, 'segundo teste de ticket3', 'estou realizando um teste novo de ticket', '', NULL, NULL, NULL, NULL, NULL, '2026-04-07 15:23:18', '2026-04-07 18:23:18', '2026-04-07 19:19:25'),
(22, 'FAT-2026-00001', 'FA0022N6T0', 20, 15, 5, 1, 1, 2, 2, 'revisar nota cancelada', 'quero muito ver se essa nota aqui já foi cancelada 44888215855589325', '', NULL, NULL, NULL, NULL, NULL, '2026-04-08 09:48:45', '2026-04-08 12:48:45', '2026-04-08 14:53:18'),
(23, 'FAT-2026-00002', 'FA0023N6T6', 20, 15, 5, 2, NULL, 2, 2, 'tests222', '222teste', '', NULL, NULL, NULL, NULL, NULL, '2026-04-08 10:20:16', '2026-04-08 13:20:16', '2026-04-08 14:53:24'),
(24, 'FAT-2026-00003', 'FA0024N6T2', 20, 15, 5, 2, NULL, 3, 2, 'novotetst', 'testaset', '', NULL, NULL, NULL, NULL, NULL, '2026-04-08 10:22:48', '2026-04-08 13:22:48', '2026-04-08 14:16:26'),
(25, 'FAT-2026-00004', 'FA0025N6T8', 20, NULL, 5, 2, NULL, 1, 2, 'segundo teste de ticket 2', 'testes', '', NULL, NULL, NULL, NULL, NULL, '2026-04-08 13:14:32', '2026-04-08 16:14:32', '2026-04-08 16:14:32');

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
  `tipo` enum('mensagem','nota_interna','alteracao_status','atribuicao','sistema','encaminhamento','atribuicao','devolucao','sla_iniciado','sla_pausado','sla_retomado','sla_concluido','sla_estourado') COLLATE utf8mb4_unicode_ci DEFAULT 'mensagem',
  `publico` tinyint(1) DEFAULT '1',
  `mensagem` longtext COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_ticket_id` (`ticket_id`),
  KEY `idx_usuario_id` (`usuario_id`),
  KEY `idx_tipo` (`tipo`),
  KEY `idx_publico` (`publico`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_comp_ticket_created` (`ticket_id`,`created_at`),
  KEY `idx_ticket_publico_criacao` (`ticket_id`,`publico`,`created_at`) COMMENT 'Carregar interações públicas/privadas de um ticket'
) ENGINE=InnoDB AUTO_INCREMENT=73 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `ticket_interacoes`
--

INSERT INTO `ticket_interacoes` (`id`, `ticket_id`, `usuario_id`, `tipo`, `publico`, `mensagem`, `created_at`, `updated_at`) VALUES
(42, 15, 15, '', 1, 'Teste após adicionar updated_at', '2026-03-31 14:33:29', '2026-03-31 14:33:29'),
(43, 17, 15, '', 1, 'testes', '2026-03-31 17:36:37', '2026-03-31 17:36:37'),
(44, 18, 15, '', 1, 'comentario para o usuario', '2026-03-31 20:37:00', '2026-03-31 20:37:00'),
(45, 18, 15, 'nota_interna', 0, 'Comentario interno', '2026-03-31 20:37:07', '2026-03-31 20:37:07'),
(46, 18, 15, 'nota_interna', 0, 'interno 2', '2026-03-31 20:38:31', '2026-03-31 20:38:31'),
(47, 18, 15, '', 1, 'para o usuario 2', '2026-03-31 20:39:13', '2026-03-31 20:39:13'),
(48, 18, 15, 'nota_interna', 0, 'comentario interno 3', '2026-03-31 21:52:10', '2026-03-31 21:52:10'),
(49, 18, 15, '', 1, 'comum 1', '2026-03-31 21:52:47', '2026-03-31 21:52:47'),
(50, 19, 15, 'nota_interna', 0, 'pedir autorizaççao', '2026-03-31 22:15:59', '2026-03-31 22:15:59'),
(51, 19, 15, '', 1, 'ok recebido', '2026-03-31 22:16:26', '2026-03-31 22:16:26'),
(52, 19, 19, '', 1, '123', '2026-04-01 17:38:21', '2026-04-01 17:38:21'),
(53, 19, 19, '', 1, '123', '2026-04-01 17:43:45', '2026-04-01 17:43:45'),
(54, 19, 15, '', 1, '23456', '2026-04-01 17:44:35', '2026-04-01 17:44:35'),
(55, 19, 19, '', 1, 'okok', '2026-04-01 17:44:48', '2026-04-01 17:44:48'),
(59, 21, 15, '', 1, 'teste 222', '2026-04-07 18:28:42', '2026-04-07 18:28:42'),
(60, 21, 15, '', 1, 'teste 222', '2026-04-07 18:51:45', '2026-04-07 18:51:45'),
(61, 21, 15, '', 1, '🔀 Ticket encaminhado para o grupo \'assistencia\' por Administrador', '2026-04-07 18:59:42', '2026-04-07 18:59:42'),
(62, 21, 23, 'atribuicao', 1, '🙋 Usuário #23 assumiu o atendimento deste chamado.', '2026-04-07 19:19:25', '2026-04-07 19:19:25'),
(63, 21, 20, '', 1, 'camila atende ok', '2026-04-07 19:20:36', '2026-04-07 19:20:36'),
(64, 23, 15, 'atribuicao', 1, '🙋 Usuário #15 assumiu o atendimento deste chamado.', '2026-04-08 13:20:27', '2026-04-08 13:20:27'),
(65, 23, 15, 'sla_iniciado', 1, '⏱️ Contagem de SLA iniciada.', '2026-04-08 13:20:27', '2026-04-08 13:20:27'),
(66, 23, 15, 'devolucao', 1, '↩️ Usuário #15 devolveu o chamado para a fila — Motivo: testse.', '2026-04-08 13:21:40', '2026-04-08 13:21:40'),
(67, 23, 15, 'sla_pausado', 1, '⏸️ SLA pausado — Motivo: testse.', '2026-04-08 13:21:40', '2026-04-08 13:21:40'),
(68, 24, 15, 'atribuicao', 1, '🙋 Usuário #15 assumiu o atendimento deste chamado.', '2026-04-08 13:23:08', '2026-04-08 13:23:08'),
(69, 24, 15, 'sla_iniciado', 1, '⏱️ Contagem de SLA iniciada.', '2026-04-08 13:23:08', '2026-04-08 13:23:08'),
(70, 22, 15, 'atribuicao', 1, '🙋 Usuário #15 assumiu o atendimento deste chamado.', '2026-04-08 14:53:18', '2026-04-08 14:53:18'),
(71, 23, 15, 'atribuicao', 1, '🙋 Usuário #15 assumiu o atendimento deste chamado.', '2026-04-08 14:53:24', '2026-04-08 14:53:24'),
(72, 23, 15, 'sla_iniciado', 1, '⏱️ Contagem de SLA iniciada.', '2026-04-08 14:53:24', '2026-04-08 14:53:24');

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
-- Estrutura para tabela `ticket_sla`
--

DROP TABLE IF EXISTS `ticket_sla`;
CREATE TABLE IF NOT EXISTS `ticket_sla` (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `ticket_id` bigint UNSIGNED NOT NULL,
  `categoria_id` int UNSIGNED NOT NULL,
  `sla_minutos` int UNSIGNED NOT NULL COMMENT 'SLA copiado da categoria no momento da abertura',
  `iniciado_em` datetime DEFAULT NULL COMMENT 'Quando o atendimento come├ºou (usu├írio assumiu)',
  `pausado_em` datetime DEFAULT NULL COMMENT 'Quando foi pausado pela ├║ltima vez',
  `minutos_pausados` int UNSIGNED NOT NULL DEFAULT '0' COMMENT 'Total de minutos j├í pausados (acumulado)',
  `status` enum('aguardando','em_andamento','pausado','concluido','estourado') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'aguardando',
  `estourou_em` datetime DEFAULT NULL COMMENT 'Momento exato em que o SLA estourou',
  `concluido_em` datetime DEFAULT NULL COMMENT 'Momento em que foi conclu├¡do dentro do prazo',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_ticket_sla` (`ticket_id`),
  KEY `idx_status` (`status`),
  KEY `idx_categoria_id` (`categoria_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Rastreamento de SLA por ticket';

--
-- Despejando dados para a tabela `ticket_sla`
--

INSERT INTO `ticket_sla` (`id`, `ticket_id`, `categoria_id`, `sla_minutos`, `iniciado_em`, `pausado_em`, `minutos_pausados`, `status`, `estourou_em`, `concluido_em`, `created_at`, `updated_at`) VALUES
(1, 23, 2, 1440, '2026-04-08 10:20:28', NULL, 91, 'em_andamento', NULL, NULL, '2026-04-08 13:20:16', '2026-04-08 14:53:24'),
(2, 24, 2, 10, '2026-04-08 10:23:09', NULL, 0, 'em_andamento', NULL, NULL, '2026-04-08 13:22:48', '2026-04-08 13:23:08'),
(3, 25, 2, 10, NULL, NULL, 0, 'aguardando', NULL, NULL, '2026-04-08 16:14:32', '2026-04-08 16:14:32');

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
  `role` enum('USER','TI','ADMIN','RESPONSAVEL_GRUPO') DEFAULT 'USER',
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
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Despejando dados para a tabela `users`
--

INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `role`, `sector`, `unit`, `is_active`, `created_at`, `username`, `department_id`, `group_id`) VALUES
(15, 'Administrador', 'admin@cpe.com.br', '$2b$12$cUzgsKcnlFpM4RLi4s6ice887vhB4RqDprqSCAeeTLpCiyhnjLkZ.', 'ADMIN', NULL, NULL, 1, '2026-03-18 21:01:36', 'admin', NULL, NULL),
(17, 'Manager System', 'manager@cpe.com.br', '$2b$12$e5owWqUGPxvGMQdM3dUVDe2O0k0vqCqRVJr.qiHqnINNk.G9K2i3O', 'TI', NULL, NULL, 1, '2026-03-18 21:01:36', 'manager', NULL, 1),
(19, 'jonathan', 'jonathan2@cpe.com.br', '$2b$12$gAsoH/SsdblwHN.kd9djQeFMXb3Kep0q8rUbfe0kNSYbPTlw.X2Xa', 'USER', NULL, NULL, 1, '2026-03-18 21:43:48', 'jonathan.lopes2', NULL, 1),
(20, 'fernanda', 'fernandateste@cpe.com.br', '$2b$12$14PTC6nIsDE1TBi9/tOGZuDT2WmTMAB3R6mdqXCZ6mMGnahe8k4Xe', 'RESPONSAVEL_GRUPO', NULL, NULL, 1, '2026-03-18 22:19:27', 'fernanda.teste', NULL, 3),
(22, 'jose', 'jose@cpe.com.br', '$2b$12$lstGgaNJYVLuzX9bI4fci.WZ8mXCHpZzyknSfeqhyztfJtmefYKii', 'RESPONSAVEL_GRUPO', NULL, NULL, 1, '2026-04-02 20:10:25', 'jose.jose', NULL, NULL),
(23, 'camila', 'camila@cpe.com.br', '$2b$12$N61JAIvgCTDXXI/H.B0ryuKI8vxcr8FayHrj5DxrXHAkreSiKg3km', 'USER', NULL, NULL, 1, '2026-04-07 18:34:51', 'camila.teste', NULL, 3);

-- --------------------------------------------------------

--
-- Estrutura para tabela `user_access_exceptions`
--

DROP TABLE IF EXISTS `user_access_exceptions`;
CREATE TABLE IF NOT EXISTS `user_access_exceptions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL COMMENT 'Usuário afetado',
  `page_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Nome da página',
  `exception_type` enum('block','allow') COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'block = bloquear, allow = permitir',
  `reason` text COLLATE utf8mb4_unicode_ci COMMENT 'Motivo da exceção',
  `created_by` int DEFAULT NULL COMMENT 'Admin que criou',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_user_page_type` (`user_id`,`page_name`,`exception_type`),
  KEY `idx_uae_user_id` (`user_id`),
  KEY `idx_uae_page_name` (`page_name`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `user_access_exceptions`
--

INSERT INTO `user_access_exceptions` (`id`, `user_id`, `page_name`, `exception_type`, `reason`, `created_by`, `created_at`) VALUES
(4, 19, 'TICKETS', 'block', '', 15, '2026-04-07 11:28:13');

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
  ADD CONSTRAINT `fk_categorias_group` FOREIGN KEY (`group_id`) REFERENCES `cpe_grupo` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `cpe_grupo`
--
ALTER TABLE `cpe_grupo`
  ADD CONSTRAINT `cpe_grupo_ibfk_1` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `passwords`
--
ALTER TABLE `passwords`
  ADD CONSTRAINT `fk_passwords_group` FOREIGN KEY (`group_id`) REFERENCES `cpe_grupo` (`id`) ON DELETE SET NULL;

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
  ADD CONSTRAINT `fk_tickets_group` FOREIGN KEY (`group_id`) REFERENCES `cpe_grupo` (`id`) ON DELETE RESTRICT,
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
