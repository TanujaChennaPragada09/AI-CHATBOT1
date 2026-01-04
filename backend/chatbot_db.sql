-- 1. Create database
CREATE DATABASE IF NOT EXISTS chatbot_db;

-- 2. Use database
USE chatbot_db;

-- 3. Create user
CREATE USER IF NOT EXISTS 'Chat_user'@'%' IDENTIFIED BY 'Admin@123';

-- 4. Grant privileges
GRANT ALL PRIVILEGES ON chatbot_db.* TO 'Chat_user'@'%';

-- 5. Apply privileges
FLUSH PRIVILEGES;

-- 6. Create messages table (REQUIRED)
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    role ENUM('user','bot') NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
