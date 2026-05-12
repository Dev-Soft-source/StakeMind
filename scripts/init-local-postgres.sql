-- Bootstrap a local PostgreSQL role and database for StakeMind development.
-- Safe to run multiple times.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'stakemind') THEN
        CREATE ROLE stakemind LOGIN PASSWORD 'stakemind';
    ELSE
        ALTER ROLE stakemind WITH LOGIN PASSWORD 'stakemind';
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'stakemind') THEN
        CREATE DATABASE stakemind OWNER stakemind;
    END IF;
END
$$;

GRANT ALL PRIVILEGES ON DATABASE stakemind TO stakemind;
