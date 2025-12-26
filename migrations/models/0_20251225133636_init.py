from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "users" (
    "id" UUID NOT NULL PRIMARY KEY,
    "username" VARCHAR(50) NOT NULL UNIQUE,
    "name" VARCHAR(100) NOT NULL,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "phone" VARCHAR(20) NOT NULL UNIQUE,
    "current_status" VARCHAR(32) NOT NULL,
    "password_hash" VARCHAR(255) NOT NULL,
    "is_admin" BOOL NOT NULL DEFAULT False,
    "is_active" BOOL NOT NULL DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_users_usernam_266d85" ON "users" ("username");
COMMENT ON COLUMN "users"."current_status" IS 'job | student | other';
CREATE TABLE IF NOT EXISTS "projects" (
    "id" UUID NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "project_root" VARCHAR(1024) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "owner_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_projects_owner_i_25f5e7" UNIQUE ("owner_id", "name")
);
CREATE INDEX IF NOT EXISTS "idx_projects_name_7b5b92" ON "projects" ("name");
CREATE TABLE IF NOT EXISTS "project_runtime" (
    "id" UUID NOT NULL PRIMARY KEY,
    "project_root" TEXT NOT NULL,
    "container_name" VARCHAR(255) NOT NULL UNIQUE,
    "image" VARCHAR(255) NOT NULL DEFAULT 'python:3.11-slim',
    "status" VARCHAR(32) NOT NULL DEFAULT 'stopped',
    "last_command" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "project_id" UUID NOT NULL UNIQUE REFERENCES "projects" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "project_runtime" IS 'Persistent runtime state for each generated project.';
CREATE TABLE IF NOT EXISTS "refresh_tokens" (
    "id" UUID NOT NULL PRIMARY KEY,
    "hashed_token" VARCHAR(60) NOT NULL UNIQUE,
    "jti" VARCHAR(36) NOT NULL UNIQUE,
    "expires_at" TIMESTAMPTZ NOT NULL,
    "is_revoked" BOOL NOT NULL DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
    "92+R4i"
)
