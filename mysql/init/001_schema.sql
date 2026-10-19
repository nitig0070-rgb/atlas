CREATE DATABASE IF NOT EXISTS project_atlas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE project_atlas;

CREATE TABLE IF NOT EXISTS clients (
  id VARCHAR(16) PRIMARY KEY,
  company VARCHAR(160) NOT NULL,
  contact_email VARCHAR(254) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reports (
  id VARCHAR(16) PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  publisher VARCHAR(160) NOT NULL,
  published DATE NOT NULL,
  sector VARCHAR(100) NOT NULL,
  access_level VARCHAR(40) NOT NULL,
  description TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS client_report_entitlements (
  client_id VARCHAR(16) NOT NULL,
  report_id VARCHAR(16) NOT NULL,
  grant_type ENUM('purchase','excerpt_grant') NOT NULL DEFAULT 'purchase',
  purchased_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (client_id, report_id),
  FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
  FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
  INDEX ix_entitlements_report (report_id)
);
CREATE TABLE IF NOT EXISTS market_metrics (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  report_id VARCHAR(16) NOT NULL,
  metric VARCHAR(80) NOT NULL,
  region VARCHAR(80) NOT NULL,
  period VARCHAR(32) NOT NULL,
  `value` DECIMAL(18,6) NOT NULL,
  unit VARCHAR(40) NOT NULL,
  scope_note VARCHAR(500) NOT NULL,
  FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
  INDEX ix_metrics_report_metric (report_id, metric)
);
CREATE TABLE IF NOT EXISTS conversations (
  id CHAR(36) PRIMARY KEY,
  client_id VARCHAR(16) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (client_id) REFERENCES clients(id),
  INDEX ix_conversations_client_created (client_id, created_at)
);
CREATE TABLE IF NOT EXISTS conversation_messages (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  conversation_id CHAR(36) NOT NULL,
  role ENUM('user','assistant') NOT NULL,
  content MEDIUMTEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
  INDEX ix_messages_conversation_created (conversation_id, created_at)
);
CREATE TABLE IF NOT EXISTS feedback (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  conversation_id CHAR(36) NOT NULL,
  message_id BIGINT NOT NULL,
  rating TINYINT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_feedback_rating CHECK (rating IN (-1, 1)),
  FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
  FOREIGN KEY (message_id) REFERENCES conversation_messages(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS escalations (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  client_id VARCHAR(16) NOT NULL,
  conversation_id CHAR(36) NOT NULL,
  question TEXT NOT NULL,
  reason VARCHAR(500) NOT NULL,
  confidence DECIMAL(5,4) NOT NULL,
  status ENUM('open','in_review','resolved') NOT NULL DEFAULT 'open',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  resolved_at TIMESTAMP NULL,
  FOREIGN KEY (client_id) REFERENCES clients(id),
  FOREIGN KEY (conversation_id) REFERENCES conversations(id),
  INDEX ix_escalations_status_created (status, created_at)
);
CREATE TABLE IF NOT EXISTS request_logs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  client_id VARCHAR(16) NULL,
  request_id CHAR(36) NOT NULL,
  latency_ms INT UNSIGNED NOT NULL,
  token_usage INT UNSIGNED NULL,
  estimated_cost DECIMAL(12,8) NULL,
  route VARCHAR(40) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_request_logs_created (created_at)
);
CREATE TABLE IF NOT EXISTS security_events (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  client_id VARCHAR(16) NULL,
  event_type VARCHAR(80) NOT NULL,
  severity ENUM('low','medium','high','critical') NOT NULL,
  details JSON NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_security_events_type_created (event_type, created_at)
);
CREATE TABLE IF NOT EXISTS cost_logs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  request_id CHAR(36) NOT NULL,
  provider VARCHAR(40) NOT NULL,
  model VARCHAR(120) NOT NULL,
  input_tokens INT UNSIGNED NULL,
  output_tokens INT UNSIGNED NULL,
  estimated_cost DECIMAL(12,8) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_cost_logs_created (created_at)
);
CREATE USER IF NOT EXISTS 'atlas_reader'@'%' IDENTIFIED BY 'change_me_reader_local_only';
GRANT SELECT ON project_atlas.* TO 'atlas_reader'@'%';
