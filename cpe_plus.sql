-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1:3306
-- Tempo de geração: 06/04/2026 às 22:41
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
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `user_access_exceptions`
--

INSERT INTO `user_access_exceptions` (`id`, `user_id`, `page_name`, `exception_type`, `reason`, `created_by`, `created_at`) VALUES
(1, 19, 'CHAT', 'block', 'teste', 15, '2026-04-06 22:40:24'),
(2, 19, 'PASSWORD_VAULT', 'block', 'teste', 15, '2026-04-06 22:40:24');
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
