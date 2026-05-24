import pytest
from errors import DBError


class TestDataTypes:
    def test_integer_stored_and_retrieved(self, db):
        db.q("CREATE TABLE t (n INTEGER)")
        db.q("INSERT INTO t VALUES (42)")
        rows = db.rows("SELECT * FROM t")
        assert rows[0][0] == "42"

    def test_real_stored_and_retrieved(self, db):
        db.q("CREATE TABLE t (x REAL)")
        db.q("INSERT INTO t VALUES (3.14)")
        rows = db.rows("SELECT * FROM t")
        assert rows[0][0] == "3.14"

    def test_boolean_true_stored_and_retrieved(self, db):
        db.q("CREATE TABLE t (flag BOOLEAN)")
        db.q("INSERT INTO t VALUES (TRUE)")
        rows = db.rows("SELECT * FROM t")
        assert rows[0][0] == "TRUE"

    def test_boolean_false_stored_and_retrieved(self, db):
        db.q("CREATE TABLE t (flag BOOLEAN)")
        db.q("INSERT INTO t VALUES (FALSE)")
        rows = db.rows("SELECT * FROM t")
        assert rows[0][0] == "FALSE"

    def test_text_stored_and_retrieved(self, db):
        db.q("CREATE TABLE t (s TEXT)")
        db.q("INSERT INTO t VALUES ('hello')")
        rows = db.rows("SELECT * FROM t")
        assert rows[0][0] == "hello"

    def test_invalid_integer_raises(self, db):
        db.q("CREATE TABLE t (n INTEGER)")
        with pytest.raises(DBError):
            db.q("INSERT INTO t VALUES ('not_a_number')")

    def test_invalid_real_raises(self, db):
        db.q("CREATE TABLE t (x REAL)")
        with pytest.raises(DBError):
            db.q("INSERT INTO t VALUES ('abc')")

    def test_invalid_boolean_raises(self, db):
        db.q("CREATE TABLE t (flag BOOLEAN)")
        with pytest.raises(DBError):
            db.q("INSERT INTO t VALUES ('yes')")

    def test_integer_equality_filter(self, db):
        db.q("CREATE TABLE t (id INTEGER, val TEXT)")
        db.q("INSERT INTO t VALUES (1, 'a')")
        db.q("INSERT INTO t VALUES (2, 'b')")
        db.q("INSERT INTO t VALUES (10, 'c')")
        assert db.row_count("SELECT * FROM t WHERE id = 1") == 1

    def test_integer_equality_large_value(self, db):
        db.q("CREATE TABLE t (n INTEGER)")
        db.q("INSERT INTO t VALUES (10)")
        db.q("INSERT INTO t VALUES (2)")
        assert db.row_count("SELECT * FROM t WHERE n = 10") == 1

    def test_real_equality_filter(self, db):
        db.q("CREATE TABLE t (price REAL, name TEXT)")
        db.q("INSERT INTO t VALUES (9.99, 'cheap')")
        db.q("INSERT INTO t VALUES (99.99, 'expensive')")
        assert db.row_count("SELECT * FROM t WHERE price = 9.99") == 1

    def test_boolean_filter(self, db):
        db.q("CREATE TABLE t (active BOOLEAN, name TEXT)")
        db.q("INSERT INTO t VALUES (TRUE, 'Alice')")
        db.q("INSERT INTO t VALUES (FALSE, 'Bob')")
        assert db.row_count("SELECT * FROM t WHERE active = TRUE") == 1

    def test_mixed_types_in_table(self, db):
        db.q("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT, score REAL, active BOOLEAN)")
        db.q("INSERT INTO t (name, score, active) VALUES ('Alice', 95.5, TRUE)")
        rows = db.rows("SELECT * FROM t")
        assert rows[0][1] == "Alice"
        assert rows[0][2] == "95.5"
        assert rows[0][3] == "TRUE"

    def test_integer_pk_autoincrement(self, db):
        db.q("CREATE TABLE t (id INTEGER PRIMARY KEY, val TEXT)")
        db.q("INSERT INTO t (val) VALUES ('a')")
        db.q("INSERT INTO t (val) VALUES ('b')")
        rows = db.rows("SELECT * FROM t")
        assert rows[0][0] == "1"
        assert rows[1][0] == "2"

    def test_update_typed_column(self, db):
        db.q("CREATE TABLE t (id INTEGER, score REAL)")
        db.q("INSERT INTO t VALUES (1, 1.5)")
        db.q("UPDATE t SET score = 9.9 WHERE id = 1")
        rows = db.rows("SELECT * FROM t")
        assert rows[0][1] == "9.9"

    def test_type_info_persists_after_reload(self, tmp_path):
        from conftest import DBMS
        path = str(tmp_path / "db")
        db = DBMS(path)
        db.q("CREATE TABLE t (n INTEGER)")
        db.q("INSERT INTO t VALUES (42)")
        db2 = DBMS(path)
        rows = db2.rows("SELECT * FROM t")
        assert rows[0][0] == "42"

    def test_integer_equality_after_reload(self, tmp_path):
        from conftest import DBMS
        path = str(tmp_path / "db")
        db = DBMS(path)
        db.q("CREATE TABLE t (n INTEGER)")
        db.q("INSERT INTO t VALUES (10)")
        db.q("INSERT INTO t VALUES (2)")
        db2 = DBMS(path)
        assert db2.row_count("SELECT * FROM t WHERE n = 10") == 1
