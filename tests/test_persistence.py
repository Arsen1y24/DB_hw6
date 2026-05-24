import pytest
from conftest import DBMS


class TestPersistence:
    def test_data_survives_reload(self, tmp_path):
        path = str(tmp_path / "db")
        db = DBMS(path)
        db.q("CREATE TABLE t (a)")
        db.q("INSERT INTO t VALUES ('hello')")
        db2 = DBMS(path)
        assert db2.row_count("SELECT * FROM t") == 1

    def test_schema_survives_reload(self, tmp_path):
        path = str(tmp_path / "db")
        db = DBMS(path)
        db.q("CREATE TABLE t (x, y)")
        db2 = DBMS(path)
        result = db2.q("SELECT * FROM t")
        assert "x" in result and "y" in result

    def test_multiple_tables_survive_reload(self, tmp_path):
        path = str(tmp_path / "db")
        db = DBMS(path)
        db.q("CREATE TABLE t1 (a)")
        db.q("CREATE TABLE t2 (b)")
        db2 = DBMS(path)
        assert db2.row_count("SELECT * FROM t1") == 0
        assert db2.row_count("SELECT * FROM t2") == 0

    def test_updated_values_survive_reload(self, tmp_path):
        path = str(tmp_path / "db")
        db = DBMS(path)
        db.q("CREATE TABLE t (a, b)")
        db.q("INSERT INTO t VALUES ('1', 'old')")
        db.q("UPDATE t SET b = 'new' WHERE a = '1'")
        db2 = DBMS(path)
        result = db2.q("SELECT * FROM t")
        assert "new" in result

    def test_deleted_rows_absent_after_reload(self, tmp_path):
        path = str(tmp_path / "db")
        db = DBMS(path)
        db.q("CREATE TABLE t (a)")
        db.q("INSERT INTO t VALUES ('keep')")
        db.q("INSERT INTO t VALUES ('drop')")
        db.q("DELETE FROM t WHERE a = 'drop'")
        db2 = DBMS(path)
        assert db2.row_count("SELECT * FROM t") == 1
        assert "keep" in db2.q("SELECT * FROM t")

    def test_dropped_table_absent_after_reload(self, tmp_path):
        from errors import DBError
        path = str(tmp_path / "db")
        db = DBMS(path)
        db.q("CREATE TABLE t (a)")
        db.q("DROP TABLE t")
        db2 = DBMS(path)
        with pytest.raises(DBError):
            db2.q("SELECT * FROM t")
