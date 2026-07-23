from dataclasses import dataclass

from sqlalchemy import Engine, text


@dataclass(frozen=True)
class SchemaMigration:
    """一条可重复执行的轻量数据库迁移。

    项目当前尚未引入 Alembic，因此先用明确版本号和幂等 PostgreSQL 语句处理开发期增量结构。
    后续引入正式迁移工具时，可以直接把这里的版本作为基线记录。
    """

    version: str
    description: str
    statements: tuple[str, ...]


SCHEMA_MIGRATIONS = (
    SchemaMigration(
        version="20260720_01_media_generation_workbench_slug",
        description="为已有媒体任务补充工作台来源字段和查询索引",
        statements=(
            """
            ALTER TABLE media_generations
            ADD COLUMN IF NOT EXISTS workbench_slug VARCHAR(80) NOT NULL DEFAULT ''
            """,
            """
            CREATE INDEX IF NOT EXISTS ix_media_generations_workbench_slug
            ON media_generations (workbench_slug)
            """,
        ),
    ),
)


def run_schema_migrations(engine: Engine) -> None:
    """在 ``create_all`` 后执行尚未登记的开发期迁移。

    PostgreSQL 的 ``ADD COLUMN IF NOT EXISTS`` 和 ``CREATE INDEX IF NOT EXISTS`` 让迁移即使在
    容器异常重启后再次运行也不会破坏已有数据。迁移记录与结构修改处于同一个事务中。
    """

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS app_schema_migrations (
                    version VARCHAR(120) PRIMARY KEY,
                    description VARCHAR(500) NOT NULL,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        applied = set(connection.execute(text("SELECT version FROM app_schema_migrations")).scalars())
        for migration in SCHEMA_MIGRATIONS:
            if migration.version in applied:
                continue
            for statement in migration.statements:
                connection.execute(text(statement))
            connection.execute(
                text(
                    """
                    INSERT INTO app_schema_migrations (version, description)
                    VALUES (:version, :description)
                    ON CONFLICT (version) DO NOTHING
                    """
                ),
                {"version": migration.version, "description": migration.description},
            )
