CREATE DATABASE visitor_management_system;

USE visitor_management_system;


-- 1. ADMIN TABLE
CREATE TABLE admin (
    admin_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    phone VARCHAR(15) NOT NULL
);


-- 2. VISITOR TABLE
CREATE TABLE visitor (
    visitor_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    email VARCHAR(150) NOT NULL,
    address VARCHAR(255) NOT NULL,
    id_proof VARCHAR(100) NOT NULL,
    admin_id INT NOT NULL,

    FOREIGN KEY (admin_id)
        REFERENCES admin(admin_id)
);


-- 3. VISIT REQUEST TABLE
CREATE TABLE visit_request (
    request_id INT PRIMARY KEY AUTO_INCREMENT,
    visitor_id INT NOT NULL,
    visit_date DATE NOT NULL,
    purpose VARCHAR(255) NOT NULL,
    status VARCHAR(30) NOT NULL,
    request_time DATETIME NOT NULL,

    FOREIGN KEY (visitor_id)
        REFERENCES visitor(visitor_id)
);


-- 4. GATE PASS TABLE
CREATE TABLE gate_pass (
    pass_id INT PRIMARY KEY AUTO_INCREMENT,
    request_id INT NOT NULL,
    visitor_id INT NOT NULL,
    issue_date DATE NOT NULL,
    valid_time TIME NOT NULL,
    status VARCHAR(30) NOT NULL,

    FOREIGN KEY (request_id)
        REFERENCES visit_request(request_id),

    FOREIGN KEY (visitor_id)
        REFERENCES visitor(visitor_id)
);


-- 5. VISIT LOG TABLE
CREATE TABLE visit_log (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    pass_id INT NOT NULL,
    in_time DATETIME NOT NULL,
    out_time DATETIME NULL,
    remarks VARCHAR(255) NULL,

    FOREIGN KEY (pass_id)
        REFERENCES gate_pass(pass_id)
);