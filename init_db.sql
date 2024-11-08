-- Create user and database
CREATE USER smsuser WITH PASSWORD 'audioplex';
CREATE DATABASE smsdb OWNER smsuser;

-- Connect to the database
\c smsdb

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE smsdb TO smsuser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO smsuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO smsuser; 