CREATE TABLE IF NOT EXISTS auth_users (
    user_id VARCHAR(36) PRIMARY KEY,
    email VARCHAR NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name VARCHAR NOT NULL,
    role VARCHAR NOT NULL DEFAULT 'founder',
    status VARCHAR NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_auth_users_email ON auth_users(email);
CREATE INDEX IF NOT EXISTS ix_auth_users_role ON auth_users(role);
CREATE INDEX IF NOT EXISTS ix_auth_users_status ON auth_users(status);
CREATE INDEX IF NOT EXISTS ix_auth_users_created_at ON auth_users(created_at);

CREATE TABLE IF NOT EXISTS auth_sessions (
    session_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES auth_users(user_id),
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    remember_me INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_auth_sessions_user_id ON auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_auth_sessions_token_hash ON auth_sessions(token_hash);
CREATE INDEX IF NOT EXISTS ix_auth_sessions_expires_at ON auth_sessions(expires_at);
CREATE INDEX IF NOT EXISTS ix_auth_sessions_created_at ON auth_sessions(created_at);
CREATE INDEX IF NOT EXISTS ix_auth_sessions_last_seen_at ON auth_sessions(last_seen_at);
