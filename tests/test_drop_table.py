import pytest
from errors import DBError


class TestDropTable:
    def test_drop_removes_table(self, db):
        db.q("CREATE TABLE t (a)")
        db.q("DROP TABLE t")
        with pytest.raises(DBError):
            db.q("SELECT * FROM t")

    def test_drop_nonexistent_table_raises(self, db):
        with pytest.raises(DBError):
            db.q("DROP TABLE ghost")

    def test_drop_table_data_is_gone(self, db):
        db.q("CREATE TABLE t (a)")
        db.q("INSERT INTO t VALUES ('x')")
        db.q("DROP TABLE t")
        with pytest.raises(DBError):
            db.q("SELECT * FROM t")

    def test_can_recreate_after_drop(self, db):
        db.q("CREATE TABLE t (a)")
        db.q("DROP TABLE t")
        db.q("CREATE TABLE t (a, b)")
        assert db.row_count("SELECT * FROM t") == 0

    def test_drop_one_table_leaves_others(self, db):
        db.q("CREATE TABLE t1 (a)")
        db.q("CREATE TABLE t2 (b)")
        db.q("INSERT INTO t1 VALUES ('x')")
        db.q("DROP TABLE t1")
        assert db.row_count("SELECT * FROM t2") == 0
