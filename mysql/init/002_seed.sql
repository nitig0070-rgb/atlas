USE project_atlas;
INSERT IGNORE INTO clients (id, company, contact_email) VALUES
('C-01','Northwind Utilities','ops@example.com'),
('C-02','Blue Delta Infra','procurement@example.com');
INSERT IGNORE INTO reports (id,title,publisher,published,sector,access_level,description) VALUES
('R-101','Global Smart Water Meter Market 2025','CMR','2025-03-10','Utilities','paid','Global smart water meter market; broad hardware, software and services scope.'),
('R-102','Smart Water Metering: Industry Outlook 2024','Aquila Insights (third party)','2024-06-18','Utilities','public excerpt','Third-party AMR / AMI hardware-only market outlook; assignment excerpt.'),
('R-103','Residential Water Purifier Market 2025','CMR','2025-01-22','Consumer Durables','paid','Residential water purifier market.'),
('R-104','Global EV Charging Infrastructure Market 2025','CMR','2025-02-14','Transportation','paid','Synthetic market report.'),
('R-105','Industrial IoT Sensors Market 2025','CMR','2025-04-02','Industrial Technology','paid','Synthetic market report.'),
('R-106','Renewable Energy Storage Market 2025','CMR','2025-05-12','Energy','paid','Synthetic market report.'),
('R-107','Global Grid Modernization Software Market 2025','CMR','2025-05-28','Utilities','paid','Synthetic market report.');
INSERT IGNORE INTO client_report_entitlements (client_id,report_id,grant_type) VALUES
('C-01','R-101','purchase'),('C-01','R-102','excerpt_grant'),('C-01','R-103','purchase'),('C-02','R-103','purchase');
INSERT INTO market_metrics (report_id,metric,region,period,`value`,unit,scope_note)
SELECT 'R-101','Market size','Global','2024',4.21,'USD billion','Includes hardware, software and services' WHERE NOT EXISTS (SELECT 1 FROM market_metrics WHERE report_id='R-101' AND metric='Market size' AND period='2024');
INSERT INTO market_metrics (report_id,metric,region,period,`value`,unit,scope_note)
SELECT 'R-101','CAGR','Global','2025-2030',11.2,'percent','Forecast period stated as 2025-2030' WHERE NOT EXISTS (SELECT 1 FROM market_metrics WHERE report_id='R-101' AND metric='CAGR' AND period='2025-2030');
INSERT INTO market_metrics (report_id,metric,region,period,`value`,unit,scope_note)
SELECT 'R-101','Regional share','APAC','2024',38,'percent','Share of global market size' WHERE NOT EXISTS (SELECT 1 FROM market_metrics WHERE report_id='R-101' AND metric='Regional share' AND period='2024');
INSERT INTO market_metrics (report_id,metric,region,period,`value`,unit,scope_note)
SELECT 'R-102','Market size','Global','2024',3.87,'USD billion','AMR / AMI hardware only' WHERE NOT EXISTS (SELECT 1 FROM market_metrics WHERE report_id='R-102' AND metric='Market size' AND period='2024');
INSERT INTO market_metrics (report_id,metric,region,period,`value`,unit,scope_note)
SELECT 'R-102','CAGR','Global','2024-2029',9.8,'percent','Different forecast window from R-101' WHERE NOT EXISTS (SELECT 1 FROM market_metrics WHERE report_id='R-102' AND metric='CAGR' AND period='2024-2029');
INSERT INTO market_metrics (report_id,metric,region,period,`value`,unit,scope_note)
SELECT 'R-102','Regional share','APAC','2024',41,'percent','Share of hardware market' WHERE NOT EXISTS (SELECT 1 FROM market_metrics WHERE report_id='R-102' AND metric='Regional share' AND period='2024');
