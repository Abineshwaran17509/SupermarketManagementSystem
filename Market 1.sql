-- Create Database
CREATE DATABASE IF NOT EXISTS supermarket;

-- Use Database
USE supermarket;

-- STOCK TABLE
CREATE TABLE IF NOT EXISTS stock (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    price DECIMAL(10,2) NOT NULL,
    quantity INT NOT NULL,
    category VARCHAR(100) NOT NULL
);

-- BILLS TABLE
CREATE TABLE IF NOT EXISTS bills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_no INT NOT NULL,
    customer_name VARCHAR(100),
    phone VARCHAR(20),
    total DECIMAL(10,2),
    discount DECIMAL(10,2) DEFAULT 0,
    final_amount DECIMAL(10,2),
    payment_mode VARCHAR(20),
    bill_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- BILL ITEMS TABLE
CREATE TABLE IF NOT EXISTS bill_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_no INT NOT NULL,
    item_name VARCHAR(100),
    category VARCHAR(100),
    quantity INT,
    price DECIMAL(10,2),
    gst_percent DECIMAL(5,2),
    total DECIMAL(10,2)
);

-- LOYALTY POINTS TABLE
CREATE TABLE IF NOT EXISTS loyalty_points (
    phone VARCHAR(20) PRIMARY KEY,
    points INT DEFAULT 0
);

-- USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL
);

-- INSERT DEFAULT USERS
INSERT IGNORE INTO users (username, password, role)
VALUES
('admin', 'your_password', 'Admin'),
('manager', 'your_password', 'Manager'),
('staff', 'your_password', 'Staff'),
('accountant', 'your_password', 'Accountant');