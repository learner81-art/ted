-- TED演讲数据库表结构
CREATE TABLE IF NOT EXISTS talks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    speaker_id INT NOT NULL COMMENT '关联speakers表ID',
    speaker_name_zh VARCHAR(100) NOT NULL COMMENT '演讲者中文名',
    speaker_name_en VARCHAR(100) NOT NULL COMMENT '演讲者英文名',
    pdf_url VARCHAR(255) COMMENT 'PDF文件URL',
    content TEXT COMMENT '演讲内容',
    content_display TEXT COMMENT '带格式的演讲内容',
    page_count INT COMMENT 'PDF页数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_speaker (speaker_id),
    FOREIGN KEY (speaker_id) REFERENCES speakers(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
