CREATE SCHEMA IF NOT EXISTS db;

CREATE TABLE IF NOT EXISTS db.test_table (
  id bigint NOT NULL GENERATED ALWAYS AS IDENTITY,
  test_col VARCHAR NOT NULL
);