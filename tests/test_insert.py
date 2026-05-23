import pytest
from errors import DBError


class TestInsert:
    def test_inserted_row_appears_in_select(self, db):
        db.q("CREATE TABLE t (id, val)")
        db.q("INSERT INTO t VALUES ('1', 'hello')")
        assert db.row_count("SELECT * FROM t") == 1

    def test_multiple_rows_can_be_inserted(self, db):
        db.q("CREATE TABLE t (id, val)")
        db.q("INSERT INTO t VALUES ('1', 'a')")
        db.q("INSERT INTO t VALUES ('2', 'b')")
        db.q("INSERT INTO t VALUES ('3', 'c')")
        assert db.row_count("SELECT * FROM t") == 3

    def test_inserted_values_are_correct(self, db):
        db.q("CREATE TABLE t (id, val)")
        db.q("INSERT INTO t VALUES ('42', 'hello')")
        rows = db.rows("SELECT * FROM t")
        assert rows[0][0] == "42"
        assert rows[0][1] == "hello"

    def test_wrong_column_count_raises(self, db):
        db.q("CREATE TABLE t (a, b)")
        with pytest.raises(DBError):
            db.q("INSERT INTO t VALUES ('only_one')")

    def test_too_many_values_raises(self, db):
        db.q("CREATE TABLE t (a)")
        with pytest.raises(DBError):
            db.q("INSERT INTO t VALUES ('x', 'extra')")

    def test_insert_into_nonexistent_table_raises(self, db):
        with pytest.raises(DBError):
            db.q("INSERT INTO ghost VALUES ('x')")

    def test_all_values_are_stored_as_strings(self, db):
        db.q("CREATE TABLE t (n)")
        db.q("INSERT INTO t VALUES ('123')")
        rows = db.rows("SELECT * FROM t")
        assert rows[0][0] == "123"
