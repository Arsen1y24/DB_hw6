import pytest
from errors import DBError


class TestPrimaryKey:
    def test_pk_column_is_present_in_output(self, db):
        db.q("CREATE TABLE t (id PRIMARY KEY, val)")
        db.q("INSERT INTO t VALUES ('1', 'a')")
        result = db.q("SELECT * FROM t")
        assert "id" in result

    def test_explicit_pk_is_stored(self, db):
        db.q("CREATE TABLE t (id PRIMARY KEY, val)")
        db.q("INSERT INTO t VALUES ('42', 'hello')")
        rows = db.rows("SELECT * FROM t")
        assert rows[0][0] == "42"

    def test_auto_increment_assigns_pk(self, db):
        db.q("CREATE TABLE t (id PRIMARY KEY, val)")
        db.q("INSERT INTO t (val) VALUES ('a')")
        rows = db.rows("SELECT * FROM t")
        assert rows[0][0] != ""

    def test_auto_increment_increments(self, db):
        db.q("CREATE TABLE t (id PRIMARY KEY, val)")
        db.q("INSERT INTO t (val) VALUES ('a')")
        db.q("INSERT INTO t (val) VALUES ('b')")
        rows = db.rows("SELECT * FROM t")
        assert rows[0][0] != rows[1][0]

    def test_duplicate_pk_raises(self, db):
        db.q("CREATE TABLE t (id PRIMARY KEY, val)")
        db.q("INSERT INTO t VALUES ('1', 'a')")
        with pytest.raises(DBError):
            db.q("INSERT INTO t VALUES ('1', 'b')")

    def test_auto_pk_after_explicit_does_not_collide(self, db):
        db.q("CREATE TABLE t (id PRIMARY KEY, val)")
        db.q("INSERT INTO t VALUES ('5', 'x')")
        db.q("INSERT INTO t (val) VALUES ('y')")
        rows = db.rows("SELECT * FROM t")
        ids = [r[0] for r in rows]
        assert len(set(ids)) == 2

    def test_update_pk_to_duplicate_raises(self, db):
        db.q("CREATE TABLE t (id PRIMARY KEY, val)")
        db.q("INSERT INTO t VALUES ('1', 'a')")
        db.q("INSERT INTO t VALUES ('2', 'b')")
        with pytest.raises(DBError):
            db.q("UPDATE t SET id = '1' WHERE id = '2'")

    def test_update_pk_to_unique_value_succeeds(self, db):
        db.q("CREATE TABLE t (id PRIMARY KEY, val)")
        db.q("INSERT INTO t VALUES ('1', 'a')")
        db.q("UPDATE t SET id = '99' WHERE id = '1'")
        assert db.row_count("SELECT * FROM t WHERE id = '99'") == 1

    def test_table_without_pk_allows_duplicate_values(self, db):
        db.q("CREATE TABLE t (val)")
        db.q("INSERT INTO t VALUES ('x')")
        db.q("INSERT INTO t VALUES ('x')")
        assert db.row_count("SELECT * FROM t") == 2

    def test_pk_seq_survives_reload(self, tmp_path):
        from conftest import DBMS
        path = str(tmp_path / "db.json")
        db = DBMS(path)
        db.q("CREATE TABLE t (id PRIMARY KEY, val)")
        db.q("INSERT INTO t (val) VALUES ('a')")
        db.q("INSERT INTO t (val) VALUES ('b')")
        db2 = DBMS(path)
        db2.q("INSERT INTO t (val) VALUES ('c')")
        rows = db2.rows("SELECT * FROM t")
        ids = [r[0] for r in rows]
        assert len(set(ids)) == 3

    def test_named_column_insert_fills_non_pk_columns(self, db):
        db.q("CREATE TABLE t (id PRIMARY KEY, name, city)")
        db.q("INSERT INTO t (name, city) VALUES ('Alice', 'Paris')")
        result = db.q("SELECT * FROM t")
        assert "Alice" in result and "Paris" in result
