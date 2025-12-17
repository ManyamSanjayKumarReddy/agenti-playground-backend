
from tortoise import Tortoise

DATABASE_URL = (
    "postgres://sanjay:sanjay321@localhost:5434/newdb"
)


async def init_db():
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={
            "models": ["agent_v1.db.models"]
        }
    )

    # Auto-create tables (development only)
    await Tortoise.generate_schemas()


async def close_db():
    await Tortoise.close_connections()
