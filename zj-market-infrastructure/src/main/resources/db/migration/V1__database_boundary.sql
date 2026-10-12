-- Infrastructure-only probe. No order, stock or payment schema is defined here.
CREATE TABLE b_database_probe (
    probe_id CHAR(36) NOT NULL PRIMARY KEY,
    probe_value VARCHAR(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
