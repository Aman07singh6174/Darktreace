CREATE DATABASE IF NOT EXISTS darktrace CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE darktrace;

CREATE TABLE IF NOT EXISTS admin_accounts (
    id TINYINT NOT NULL PRIMARY KEY CHECK (id = 1),
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_suspended BOOLEAN NOT NULL DEFAULT FALSE,
    blocked_at DATETIME NULL,
    blocked_until DATETIME NULL,
    session_version INT NOT NULL DEFAULT 0,
    last_login DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS monitored_users (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    display_name VARCHAR(120) NOT NULL,
    department VARCHAR(80) NOT NULL DEFAULT 'Research',
    status VARCHAR(24) NOT NULL DEFAULT 'Active',
    risk_score TINYINT UNSIGNED NOT NULL DEFAULT 0,
    risk_level VARCHAR(16) NOT NULL DEFAULT 'Low',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_suspended BOOLEAN NOT NULL DEFAULT FALSE,
    blocked_at DATETIME NULL,
    blocked_until DATETIME NULL,
    session_version INT NOT NULL DEFAULT 0,
    last_seen DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_monitored_users_risk (risk_score),
    INDEX ix_monitored_users_block (blocked_until)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS communities (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE,
    description VARCHAR(500) NOT NULL,
    topic VARCHAR(80) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS community_posts (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    community_id INT NOT NULL,
    user_id INT NOT NULL,
    content VARCHAR(1000) NOT NULL,
    risk_score TINYINT UNSIGNED NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_community_posts_user (user_id),
    INDEX ix_community_posts_created (created_at),
    CONSTRAINT fk_posts_community FOREIGN KEY (community_id) REFERENCES communities(id) ON DELETE CASCADE,
    CONSTRAINT fk_posts_user FOREIGN KEY (user_id) REFERENCES monitored_users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS threat_reports (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    threat_id VARCHAR(32) NOT NULL UNIQUE,
    threat_type VARCHAR(100) NOT NULL,
    risk_level VARCHAR(16) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'Open',
    source_type VARCHAR(80) NOT NULL,
    detected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR(1200) NOT NULL,
    related_user_id INT NULL,
    analyst_status VARCHAR(24) NOT NULL DEFAULT 'Needs review',
    INDEX ix_threat_reports_detected (detected_at),
    CONSTRAINT fk_reports_user FOREIGN KEY (related_user_id) REFERENCES monitored_users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS security_logs (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    event_type VARCHAR(80) NOT NULL,
    details VARCHAR(800) NOT NULL,
    source_ip VARCHAR(45) NOT NULL,
    risk_points TINYINT UNSIGNED NOT NULL DEFAULT 0,
    risk_level VARCHAR(16) NOT NULL DEFAULT 'Low',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_security_logs_user (user_id),
    INDEX ix_security_logs_event (event_type),
    INDEX ix_security_logs_created (created_at),
    CONSTRAINT fk_security_logs_user FOREIGN KEY (user_id) REFERENCES monitored_users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS security_alerts (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    title VARCHAR(160) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    message VARCHAR(800) NOT NULL,
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_security_alerts_user (user_id),
    INDEX ix_security_alerts_severity (severity),
    INDEX ix_security_alerts_created (created_at),
    CONSTRAINT fk_security_alerts_user FOREIGN KEY (user_id) REFERENCES monitored_users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS login_attempts (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL,
    succeeded BOOLEAN NOT NULL DEFAULT FALSE,
    source_ip VARCHAR(45) NOT NULL,
    attempted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_login_attempts_username (username),
    INDEX ix_login_attempts_ip (source_ip),
    INDEX ix_login_attempts_time (attempted_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS admin_actions (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    action VARCHAR(80) NOT NULL,
    target_user_id INT NULL,
    details VARCHAR(800) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_admin_actions_target (target_user_id),
    INDEX ix_admin_actions_created (created_at),
    CONSTRAINT fk_admin_actions_user FOREIGN KEY (target_user_id) REFERENCES monitored_users(id) ON DELETE SET NULL
) ENGINE=InnoDB;