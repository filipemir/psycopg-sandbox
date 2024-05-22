# Reproducing Psycopg Transaction Mystery

This is a small isolated reproduction of an issue that's puzzled me with Psycopg's
handling of transactions and its connection contexts

To run:

```
$ docker compose build

$ docker compose run python
```

You should see output like this:

```
 ⠿ Container psycopg-issue-db-1  Running
NOTICE:  schema "db" already exists, skipping
CREATE SCHEMA
NOTICE:  relation "test_table" already exists, skipping
CREATE TABLE


Run queries commands with autocommit disabled (default):
Record fetched using connection <psycopg.AsyncConnection [INTRANS] (host=db database=postgres) at 0xffffbba324d0>:
None
Record inserted using connection <psycopg.AsyncConnection [INTRANS] (host=db database=postgres) at 0xffffbba324d0>:
(1, 'foo')
Record fetched using connection <psycopg.AsyncConnection [INTRANS] (host=db database=postgres) at 0xffffbba32c80>:
None
Record fetched using connection <psycopg.AsyncConnection [INTRANS] (host=db database=postgres) at 0xffffbba32c80>:
(1, 'foo')


Run queries commands with autocommit enabled:
Record fetched using connection <psycopg.AsyncConnection [IDLE] (host=db database=postgres) at 0xffffbba32e00>:
None
Record inserted using connection <psycopg.AsyncConnection [INTRANS] (host=db database=postgres) at 0xffffbba32e00>:
(1, 'foo')
Record fetched using connection <psycopg.AsyncConnection [IDLE] (host=db database=postgres) at 0xffffbba324d0>:
(1, 'foo')
Record fetched using connection <psycopg.AsyncConnection [IDLE] (host=db database=postgres) at 0xffffbba324d0>:
(1, 'foo')
```

The puzzling behavior to me is the fact that, in the first set of commands, the first
fetch after the insert returns `None`. I'd expect the connection context in which the
preceding select statements are executed to commit that transaction, instead of
requiring an explicit commit. The second set of commands demonstrates that setting
`autocommit` to `True` does resolve the issue.

I found the DB logs instructive here too. For the first set of commands,
notice the `BEGIN`, `SAVEPOINT` and `COMMIT` statements:

```
2024-05-22 16:47:09.679 UTC [6607] LOG:  execute <unnamed>: BEGIN
2024-05-22 16:47:09.682 UTC [6607] LOG:  execute <unnamed>:
	            SELECT * FROM db.test_table
	            WHERE id=$1

2024-05-22 16:47:09.682 UTC [6607] DETAIL:  parameters: $1 = '1'
2024-05-22 16:47:09.683 UTC [6607] LOG:  execute <unnamed>: SAVEPOINT "_pg3_1"
2024-05-22 16:47:09.684 UTC [6607] LOG:  execute <unnamed>:
	                INSERT INTO db.test_table(
	                    id, test_col
	                ) VALUES (
	                    $1, $2
	                ) RETURNING *;

2024-05-22 16:47:09.684 UTC [6607] DETAIL:  parameters: $1 = '1', $2 = 'foo'
2024-05-22 16:47:09.686 UTC [6607] LOG:  execute <unnamed>: RELEASE "_pg3_1"
2024-05-22 16:47:09.686 UTC [6608] LOG:  execute <unnamed>: BEGIN
2024-05-22 16:47:09.688 UTC [6608] LOG:  execute <unnamed>:
	            SELECT * FROM db.test_table
	            WHERE id=$1

2024-05-22 16:47:09.688 UTC [6608] DETAIL:  parameters: $1 = '1'
2024-05-22 16:47:09.689 UTC [6607] LOG:  execute <unnamed>: COMMIT
2024-05-22 16:47:09.692 UTC [6608] LOG:  execute <unnamed>:
	            SELECT * FROM db.test_table
	            WHERE id=$1

2024-05-22 16:47:09.692 UTC [6608] DETAIL:  parameters: $1 = '1'
2024-05-22 16:47:09.693 UTC [6607] LOG:  execute <unnamed>: BEGIN
2024-05-22 16:47:09.694 UTC [6607] LOG:  statement:
	            DELETE FROM db.test_table;

2024-05-22 16:47:09.696 UTC [6607] LOG:  execute <unnamed>: COMMIT
```

And for the second set of commands, notice that the only `BEGIN` and
`COMMIT` statements are the ones introduced in the one explicit
transaction for the `INSERT` statement:

```
2024-05-22 16:47:09.736 UTC [6609] LOG:  execute <unnamed>:
	            SELECT * FROM db.test_table
	            WHERE id=$1

2024-05-22 16:47:09.736 UTC [6609] DETAIL:  parameters: $1 = '1'
2024-05-22 16:47:09.737 UTC [6609] LOG:  execute <unnamed>: BEGIN
2024-05-22 16:47:09.737 UTC [6609] LOG:  execute <unnamed>:
	                INSERT INTO db.test_table(
	                    id, test_col
	                ) VALUES (
	                    $1, $2
	                ) RETURNING *;

2024-05-22 16:47:09.737 UTC [6609] DETAIL:  parameters: $1 = '1', $2 = 'foo'
2024-05-22 16:47:09.740 UTC [6609] LOG:  execute <unnamed>: COMMIT
2024-05-22 16:47:09.746 UTC [6610] LOG:  execute <unnamed>:
	            SELECT * FROM db.test_table
	            WHERE id=$1

2024-05-22 16:47:09.746 UTC [6610] DETAIL:  parameters: $1 = '1'
2024-05-22 16:47:09.747 UTC [6610] LOG:  execute <unnamed>:
	            SELECT * FROM db.test_table
	            WHERE id=$1

2024-05-22 16:47:09.747 UTC [6610] DETAIL:  parameters: $1 = '1'
2024-05-22 16:47:09.748 UTC [6609] LOG:  statement:
	            DELETE FROM db.test_table;

```
