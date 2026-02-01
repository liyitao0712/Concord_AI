-- init-db.sql
-- PostgreSQL 初始化脚本
-- 在容器首次启动时自动执行
--
-- 创建 Temporal 所需的数据库

-- 创建 Temporal 数据库（如果不存在）
SELECT 'CREATE DATABASE temporal'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'temporal')\gexec

SELECT 'CREATE DATABASE temporal_visibility'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'temporal_visibility')\gexec
