CREATE DATABASE sales;
USE sales;

-- Products Table
CREATE TABLE products (
    product_ID VARCHAR(20) PRIMARY KEY,
    p_Name VARCHAR(50),
    price DECIMAL(10,2)
);

-- Sales Table
CREATE TABLE sales (
    sale_id INT AUTO_INCREMENT PRIMARY KEY,
    sale_date DATE
);

-- Sale Items Table
CREATE TABLE sale_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sale_id INT,
    product_id VARCHAR(20),
    quantity INT,
    total_price DECIMAL(10,2),
    FOREIGN KEY (sale_id) REFERENCES sales(sale_id),
    FOREIGN KEY (product_id) REFERENCES products(product_ID)
);