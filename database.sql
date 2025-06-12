-- 创建数据库（UTF8MB4支持完整emoji和特殊字符）
CREATE DATABASE IF NOT EXISTS IDS 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE IDS;

-- 用户表（专利代理人/审查员）
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    full_name VARCHAR(100),
    title VARCHAR(50),
    phone VARCHAR(20),
    email_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    last_login DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_active (is_active),
    INDEX idx_user_email_verified (email_verified)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 专利提交记录表
CREATE TABLE IF NOT EXISTS submissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    patent_number VARCHAR(50) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_size INT,
    
    -- 专利元数据
    title_zh VARCHAR(500),
    title_en VARCHAR(500),
    abstract_zh TEXT,
    abstract_en TEXT,
    applicants TEXT,  -- JSON格式存储
    inventors TEXT,   -- JSON格式存储
    application_date DATE,
    publication_date DATE,
    ipc_classes VARCHAR(200),
    
    -- 处理状态
    status ENUM(
        'uploaded',    -- 已上传
        'parsing',     -- 解析中
        'parsed',      -- 已解析
        'searching',   -- 检索中
        'translating', -- 翻译中
        'reviewing',   -- 审核中
        'completed',   -- 已完成
        'failed'       -- 处理失败
    ) DEFAULT 'uploaded' NOT NULL,
    
    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at DATETIME,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_submission_patent (patent_number),
    INDEX idx_submission_status (status),
    INDEX idx_submission_user (user_id),
    INDEX idx_submission_date (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 专利翻译记录表
CREATE TABLE IF NOT EXISTS translations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    submission_id INT NOT NULL,
    
    -- 翻译内容
    source_text TEXT NOT NULL,
    translated_text TEXT,
    translation_source ENUM(
        'epo',      -- 欧洲专利局
        'baidu',    -- 百度翻译
        'google',   -- Google翻译
        'manual'    -- 人工翻译
    ) NOT NULL,
    
    -- 质量检查
    grammar_checked BOOLEAN DEFAULT FALSE,
    grammar_issues TEXT,  -- JSON格式存储
    reviewed_by INT,
    review_notes TEXT,
    
    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_translation_submission (submission_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 文件存储表（多版本支持）
CREATE TABLE IF NOT EXISTS files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    submission_id INT NOT NULL,
    
    -- 文件属性
    file_type ENUM(
        'original',     -- 原始文件
        'parsed',       -- 解析后的文本
        'translated',   -- 翻译结果
        'export_pdf',   -- 导出的PDF
        'export_docx',  -- 导出的Word
        'export_other'  -- 其他格式
    ) NOT NULL,
    
    file_path VARCHAR(512) NOT NULL,
    file_format VARCHAR(10) NOT NULL,  -- pdf/docx/txt等
    file_size INT,
    version INT DEFAULT 1,
    
    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE,
    INDEX idx_file_submission (submission_id),
    INDEX idx_file_type (file_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 操作审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    submission_id INT,
    
    -- 操作信息
    action VARCHAR(50) NOT NULL,  -- login/upload/download等
    ip_address VARCHAR(45),
    user_agent TEXT,
    details TEXT,  -- JSON格式
    
    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE SET NULL,
    INDEX idx_audit_user (user_id),
    INDEX idx_audit_action (action),
    INDEX idx_audit_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 初始化系统管理员（密码需要替换为实际哈希值）
INSERT INTO users (username, email, password_hash, full_name, title, email_verified, is_active)
VALUES (
    'admin',
    'admin@example.com',
    '$2b$12$EXAMPLEHASHEXAMPLEHASHEXAMPLEHASH', -- 替换为实际哈希
    '系统管理员',
    '系统管理员',
    TRUE,
    TRUE
) ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- 创建视图：专利提交统计视图
CREATE OR REPLACE VIEW submission_stats AS
SELECT 
    u.id AS user_id,
    u.username,
    COUNT(s.id) AS total_submissions,
    SUM(CASE WHEN s.status = 'completed' THEN 1 ELSE 0 END) AS completed_count,
    SUM(CASE WHEN s.status IN ('uploaded', 'parsing', 'parsed') THEN 1 ELSE 0 END) AS pending_count,
    MAX(s.created_at) AS last_submission
FROM users u
LEFT JOIN submissions s ON u.id = s.user_id
GROUP BY u.id, u.username;

-- 创建事件：定期清理未完成的上传（30天前的）
DELIMITER //
CREATE EVENT IF NOT EXISTS clean_expired_submissions
ON SCHEDULE EVERY 1 DAY
DO
BEGIN
    DELETE FROM submissions 
    WHERE status = 'uploaded' 
    AND created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);
END //
DELIMITER ;