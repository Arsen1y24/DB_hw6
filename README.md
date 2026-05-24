# Simple File-Based DBMS

Minimal SQL engine. Data is stored in binary paged files (slotted-page heap, NSM). No indexing — full table scan for every query.

## Run

```
python3 src/main.py [db_dir]
```

## Supported SQL

### CREATE TABLE

```sql
CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, height REAL, premium BOOLEAN)
CREATE TABLE logs (message TEXT, level TEXT)
```

Column types: `INTEGER`, `REAL`, `TEXT`, `BOOLEAN`. Optional `PRIMARY KEY` — auto-incremented if not provided on insert.

### INSERT

```sql
-- auto-assign pk, named columns
INSERT INTO users (name, height, premium) VALUES ('Alice', 1.68, TRUE)

-- all columns positionally, explicit pk
INSERT INTO users VALUES (2, 'Bob', 1.82, TRUE)

-- named columns in different order
INSERT INTO users (premium, name, height) VALUES (FALSE, 'Carol', 1.71)
```

### SELECT

```sql
SELECT * FROM users
SELECT name, height FROM users
SELECT * FROM users WHERE name = 'Alice'
SELECT * FROM users WHERE premium = TRUE AND name = 'Alice'
SELECT * FROM users WHERE premium = TRUE OR name = 'Carol'
SELECT * FROM users WHERE NOT premium = TRUE
SELECT * FROM users WHERE (premium = TRUE OR name = 'Carol') AND name = 'Alice'
```

### UPDATE

```sql
UPDATE users SET premium = TRUE WHERE id = 1
UPDATE users SET premium = TRUE, name = 'Alicia' WHERE id = 1
UPDATE users SET premium = FALSE
```

### DELETE

```sql
DELETE FROM users WHERE id = 1
DELETE FROM users
```

### DROP TABLE

```sql
DROP TABLE users
```

## WHERE

Supports `=`, `AND`, `OR`, `NOT`, parentheses. AND binds tighter than OR.

## Session example

```
$ python3 src/main.py

db> CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, height REAL, premium BOOLEAN)
Table 'users' created.

db> INSERT INTO users (name, height, premium) VALUES ('Alice', 1.68, TRUE)
1 row inserted.

db> INSERT INTO users VALUES (2, 'Bob', 1.82, TRUE)
1 row inserted.

db> INSERT INTO users (premium, name, height) VALUES (FALSE, 'Carol', 1.71)
1 row inserted.

db> SELECT * FROM users
id | name  | height | premium
---+-------+--------+-------
1  | Alice | 1.68   | TRUE
2  | Bob   | 1.82   | TRUE
3  | Carol | 1.71   | FALSE
(3 rows)

db> SELECT * FROM users WHERE premium = TRUE
id | name  | height | premium
---+-------+--------+-------
1  | Alice | 1.68   | TRUE
2  | Bob   | 1.82   | TRUE
(2 rows)

db> DELETE FROM users WHERE height = 1.71
1 row(s) deleted.

db> SELECT * FROM users
id | name  | height | premium
---+-------+--------+-------
1  | Alice | 1.68   | TRUE
2  | Bob   | 1.82   | TRUE
(2 rows)

db> DROP TABLE users
Table 'users' dropped.

db> EXIT
```

## Files

| File | Role |
|---|---|
| `src/main.py` | REPL entry point |
| `src/storage.py` | Paged binary storage (slotted pages) |
| `src/datatypes.py` | Type coercion and binary serialization |
| `src/parser.py` | SQL → AST |
| `src/engine.py` | Executes AST against storage |
| `src/errors.py` | `DBError` |
| `<db_dir>/` | `catalog.json` + `<table>.dat` per table |

## Tests

```
python3 -m pytest
```
