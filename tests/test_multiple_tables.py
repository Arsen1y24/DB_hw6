class TestMultipleTables:
    def test_inserts_go_to_correct_table(self, db):
        db.q("CREATE TABLE t1 (a)")
        db.q("CREATE TABLE t2 (b)")
        db.q("INSERT INTO t1 VALUES ('x')")
        assert db.row_count("SELECT * FROM t1") == 1
        assert db.row_count("SELECT * FROM t2") == 0

    def test_delete_from_one_does_not_affect_other(self, db):
        db.q("CREATE TABLE t1 (a)")
        db.q("CREATE TABLE t2 (a)")
        db.q("INSERT INTO t1 VALUES ('x')")
        db.q("INSERT INTO t2 VALUES ('y')")
        db.q("DELETE FROM t1")
        assert db.row_count("SELECT * FROM t2") == 1

    def test_tables_have_independent_schemas(self, db):
        db.q("CREATE TABLE t1 (x, y)")
        db.q("CREATE TABLE t2 (a, b, c)")
        db.q("INSERT INTO t1 VALUES ('1', '2')")
        db.q("INSERT INTO t2 VALUES ('1', '2', '3')")
        r1 = db.q("SELECT * FROM t1")
        r2 = db.q("SELECT * FROM t2")
        assert "x" in r1 and "a" in r2
