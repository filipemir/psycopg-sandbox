import asyncio
from psycopg import AsyncConnection


async def get_connection():
    return await AsyncConnection.connect(
        "postgres://postgres:postgres@db:5432/?sslmode=disable"
    )


async def insert_record(connection):
    async with connection.transaction():
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO db.test_table(
                    test_col
                ) VALUES (
                    'foo'
                ) RETURNING *
                """
            )

            print(await cursor.fetchone())


async def print_record(connection):
    async with connection.cursor() as cursor:
        await cursor.execute(
            """
            SELECT * FROM db.test_table
            """
        )

        print(await cursor.fetchall())


async def doit():
    connection_1 = await get_connection()
    connection_2 = await get_connection()

    await insert_record(connection_1)
    await print_record(connection_2)


if __name__ == "__main__":
    asyncio.run(doit())
