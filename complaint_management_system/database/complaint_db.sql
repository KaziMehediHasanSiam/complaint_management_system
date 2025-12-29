
-- Users table
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(500) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Complaints table
CREATE TABLE IF NOT EXISTS complaint (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    priority VARCHAR(20) DEFAULT 'Medium',
    status VARCHAR(20) DEFAULT 'Open',
    user_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user (id)
);

-- Responses table
CREATE TABLE IF NOT EXISTS response (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL,
    staff_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (complaint_id) REFERENCES complaint (id),
    FOREIGN KEY (staff_id) REFERENCES user (id)
);

-- Insert sample users
INSERT INTO user (username, email, password_hash, role) VALUES 
('admin', 'admin@example.com', 'admin123', 'admin'),
('staff1', 'staff1@example.com', 'staff123', 'staff'),
('user1', 'user1@example.com', 'user123', 'user');


SHOW TABLES;

DESCRIBE user;
DESCRIBE complaint;
DESCRIBE response;