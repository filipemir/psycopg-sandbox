import asyncio
from psycopg import AsyncConnection


async def get_connection():
    con = await AsyncConnection.connect(
        "postgres://postgres:postgres@db:5432/?sslmode=disable"
    )
    return con


async def insert_record(connection, record_id, value):
    async with connection.transaction():
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO db.test_table(
                    id, test_col
                ) VALUES (
                    %(id)s, %(value)s
                ) RETURNING *;
                """,
                params={"id": record_id, "value": value},
            )

            record = await cursor.fetchone()

            print(f"Record inserted using connection {connection}:")
            print(record)

            return record


async def print_record(connection, record_id):
    async with connection.cursor() as cursor:
        await cursor.execute(
            """
            SELECT * FROM db.test_table
            WHERE id=%(id)s
            """,
            params={"id": record_id},
        )

        print(f"Record fetched using connection {connection}:")
        print(await cursor.fetchone())


async def drop_records(connection):
    async with connection.cursor() as cursor:
        await cursor.execute(
            """
            DELETE FROM db.test_table;
            """,
        )
        await connection.commit()


async def reproduce_transaction_issue(autocommit_writes):
    con1 = await get_connection()
    con2 = await get_connection()

    if autocommit_writes:
        await con1.set_autocommit(True)
        await con2.set_autocommit(True)

    try:
        # If autocomit is not set to True, the
        # SELECT statement here initates a transaction that is not,
        # despite the connection context in which the statement
        # is executed, automatically committed:
        await print_record(con1, record_id=1)

        # This INSERT statement is not automatically commited
        # because the transaction initated above is has yet to be
        # comitted. Both statements then are in the same transaction
        await insert_record(con1, record_id=1, value="foo")

        # This command will be executed on a separate connection so
        # it will not have access to the data inserted (but not yet
        # committed) in the previous statement:
        await print_record(con2, record_id=1)

        # Comitting the transaction explicitly commits the INSERT
        # (and the SELECT):
        await con1.commit()

        # Now the record is available to the other connection:
        await print_record(con2, record_id=1)
    finally:
        await drop_records(con1)


if __name__ == "__main__":
    print("\n\nRun queries commands with autocommit disabled (default):")
    asyncio.run(reproduce_transaction_issue(autocommit_writes=False))

    print("\n\nRun queries commands with autocommit enabled:")
    asyncio.run(reproduce_transaction_issue(autocommit_writes=True))
