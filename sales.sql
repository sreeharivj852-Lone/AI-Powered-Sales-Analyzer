-- =====================================================================
-- Sales Analyzer & AI Assistant Database Schema
-- Database: sales
-- =====================================================================

CREATE DATABASE IF NOT EXISTS sales;
USE sales;

-- ---------------------------------------------------------------------
-- Table: products
-- Stores product inventory details
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    product_ID VARCHAR(20) PRIMARY KEY,
    p_Name VARCHAR(50) NOT NULL,
    price DECIMAL(10,2) NOT NULL
);

-- ---------------------------------------------------------------------
-- Table: sales
-- Stores sales transactions header
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sales (
    sale_id INT AUTO_INCREMENT PRIMARY KEY,
    sale_date DATE NOT NULL
);

-- ---------------------------------------------------------------------
-- Table: sale_items
-- Stores line-item details for each sale
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sale_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sale_id INT NOT NULL,
    product_id VARCHAR(20) NOT NULL,
    quantity INT NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (sale_id) REFERENCES sales(sale_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_ID)
);

-- =====================================================================
-- SECURITY: Dedicated Read-Only User for AI Chatbot (Defense-in-Depth)
-- =====================================================================
-- It is strongly recommended to run the AI assistant with a dedicated
-- MySQL user possessing strictly SELECT permissions. Even if an AI-generated
-- query bypasses application-level validation, the database engine itself
-- will reject any INSERT, UPDATE, DELETE, DROP, or administrative commands.
--
-- Run these commands as MySQL root or administrator:
--
-- CREATE USER IF NOT EXISTS 'sales_readonly'@'localhost' IDENTIFIED BY 'ChangeThisPassword123!';
-- GRANT SELECT ON sales.* TO 'sales_readonly'@'localhost';
-- FLUSH PRIVILEGES;
--
-- Then configure CHATBOT_DB_USER and CHATBOT_DB_PASSWORD in your .env file:
-- CHATBOT_DB_USER=sales_readonly
-- CHATBOT_DB_PASSWORD=ChangeThisPassword123!
-- =====================================================================
