import pytest
from errors import DBError


class TestCreateTable:
    def test_created_table_is_queryable(self, db):
        db.q("CREATE TABLE items (id, title)")
        assert db.q("SELECT * FROM items") is not None

    def test_created_table_starts_empty(self, db):
        db.q("CREATE TABLE items (id, title)")
        assert db.row_count("SELECT * FROM items") == 0

    def test_can_create_multiple_tables(self, db):
        db.q("CREATE TABLE t1 (a)")
        db.q("CREATE TABLE t2 (b)")
        assert db.row_count("SELECT * FROM t1") == 0
        assert db.row_count("SELECT * FROM t2") == 0

    def test_duplicate_table_name_raises(self, db):
        db.q("CREATE TABLE t (a)")
        with pytest.raises(DBError):
            db.q("CREATE TABLE t (a)")

    def test_columns_are_defined_at_creation(self, db):
        db.q("CREATE TABLE t (x, y, z)")
        db.q("INSERT INTO t VALUES ('1', '2', '3')")
        result = db.q("SELECT * FROM t")
        assert "x" in result and "y" in result and "z" in result
