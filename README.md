# Custom DBMS

## Run

```
python3 src/main.py [db.json]
```

## Supported SQL

### CREATE TABLE

```sql
CREATE TABLE users (id PRIMARY KEY, name, city)
CREATE TABLE logs (message, level)
```

One column may be declared `PRIMARY KEY`. Its value is auto-assigned on insert (1, 2, 3, …) unless you provide it explicitly. Uniqueness is enforced.

### INSERT

```sql
-- auto-assign primary key
INSERT INTO users (name, city) VALUES ('Alice', 'Paris')

-- explicit primary key value
INSERT INTO users VALUES ('99', 'Bob', 'London')

-- table with no primary key
INSERT INTO logs VALUES ('started', 'info')
```

### SELECT

```sql
SELECT * FROM users
SELECT name, city FROM users
SELECT * FROM users WHERE city = 'Paris'
SELECT * FROM users WHERE city = 'Paris' AND name = 'Alice'
SELECT * FROM users WHERE city = 'Paris' OR city = 'London'
SELECT * FROM users WHERE NOT city = 'Paris'
SELECT * FROM users WHERE (city = 'Paris' OR city = 'London') AND name = 'Alice'
```

### UPDATE

```sql
UPDATE users SET city = 'Berlin' WHERE id = '1'
UPDATE users SET city = 'Berlin', name = 'Alicia' WHERE id = '1'
UPDATE users SET city = 'Unknown'
```

### DELETE

```sql
DELETE FROM users WHERE id = '1'
DELETE FROM users
```

### DROP TABLE

```sql
DROP TABLE users
```

## WHERE

WHERE supports exact-match (`=`) with `AND`, `OR`, `NOT`, and parentheses.

| Construct | Example |
|---|---|
| `=` | `city = 'Paris'` |
| `AND` | `city = 'Paris' AND name = 'Alice'` |
| `OR` | `city = 'Paris' OR city = 'London'` |
| `NOT` | `NOT city = 'Paris'` |
| `( )` | `(city = 'Paris' OR city = 'London') AND name = 'Alice'` |

`AND` binds tighter than `OR` (standard SQL precedence).

## Session example

```
$ python3 src/main.py

db> CREATE TABLE users (id PRIMARY KEY, name, city)
Table 'users' created.

db> INSERT INTO users (name, city) VALUES ('Alice', 'Paris')
1 row inserted.

db> INSERT INTO users (name, city) VALUES ('Bob', 'London')
1 row inserted.

db> INSERT INTO users (name, city) VALUES ('Carol', 'Paris')
1 row inserted.

db> SELECT * FROM users
id | name  | city  
---+-------+-------
1  | Alice | Paris 
2  | Bob   | London
3  | Carol | Paris 
(3 rows)

db> SELECT * FROM users WHERE city = 'Paris' OR city = 'London'
id | name  | city  
---+-------+-------
1  | Alice | Paris 
2  | Bob   | London
3  | Carol | Paris 
(3 rows)

db> SELECT * FROM users WHERE city = 'Paris' AND NOT name = 'Carol'
id | name  | city 
---+-------+------
1  | Alice | Paris
(1 row)

db> UPDATE users SET city = 'Berlin' WHERE id = '2'
1 row(s) updated.

db> SELECT name, city FROM users
name  | city  
------+-------
Alice | Paris 
Bob   | Berlin
Carol | Paris 
(3 rows)

db> DELETE FROM users WHERE city = 'Paris'
2 row(s) deleted.

db> SELECT * FROM users
id | name | city  
---+------+-------
2  | Bob  | Berlin
(1 row)

db> drop table users
Table 'users' dropped.

db> EXIT
```

```
Intermediate state (after UPDATE users SET city = 'Berlin' WHERE id = '2'):
{
  "tables": {
    "users": {
      "columns": [
        "id",
        "name",
        "city"
      ],
      "pk": "id",
      "pk_seq": 3,
      "rows": [
        [
          "1",
          "Alice",
          "Paris"
        ],
        [
          "2",
          "Bob",
          "Berlin"
        ],
        [
          "3",
          "Carol",
          "Paris"
        ]
      ]
    }
  }
} 
```

## Files

| File | Role |
|---|---|
| `src/main.py` | REPL entry point |
| `src/storage.py` | JSON load/save with atomic writes |
| `src/parser.py` | SQL string -> AST |
| `src/engine.py` | AST -> result, table formatting |
| `src/errors.py` | `DBError` exception |
| `tests/` | pytest test suite |
| `db.json` | Data file (auto-created) |

## Tests

```
python3 -m pytest
```
