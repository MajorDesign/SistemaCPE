-- ============================================================
-- MÓDULO DE FROTAS — Migration 027
-- Data: 2026-05-07
-- Descrição: Sistema "Avise-me" — usuário se inscreve para ser
-- notificado quando o veículo voltar à empresa (status retorna
-- para 'ativo' após vistoria de retorno).
-- ============================================================

USE cpe_plus;

CREATE TABLE IF NOT EXISTS fleet_vehicle_subscriptions (
    id          INT NOT NULL AUTO_INCREMENT,
    vehicle_id  INT NOT NULL,
    user_id     BIGINT NOT NULL,
    tipo        VARCHAR(30) NOT NULL DEFAULT 'return',
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_fleet_sub (vehicle_id, user_id, tipo),
    KEY idx_fleet_sub_user (user_id),
    KEY idx_fleet_sub_vehicle (vehicle_id),
    CONSTRAINT fk_fleet_sub_vehicle
        FOREIGN KEY (vehicle_id) REFERENCES fleet_vehicles(id) ON DELETE CASCADE,
    CONSTRAINT fk_fleet_sub_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
