import pytest
from errors import DBError


class TestSelect:
    def test_select_star_returns_all_rows(self, db_with_users):
        assert db_with_users.row_count("SELECT * FROM users") == 3

    def test_select_star_returns_all_columns(self, db_with_users):
        result = db_with_users.q("SELECT * FROM users")
        assert "id" in result and "name" in result and "city" in result

    def test_select_named_columns_shows_only_those(self, db_with_users):
        result = db_with_users.q("SELECT name FROM users")
        assert "name" in result
        assert "id" not in result.splitlines()[0]
        assert "city" not in result.splitlines()[0]

    def test_select_named_columns_values_are_correct(self, db_with_users):
        result = db_with_users.q("SELECT name FROM users")
        assert "Alice" in result and "Bob" in result and "Carol" in result

    def test_select_from_nonexistent_table_raises(self, db):
        with pytest.raises(DBError):
            db.q("SELECT * FROM ghost")

    def test_select_unknown_column_raises(self, db_with_users):
        with pytest.raises(DBError):
            db_with_users.q("SELECT ghost FROM users")

    def test_select_empty_table_returns_zero_rows(self, db):
        db.q("CREATE TABLE t (a)")
        assert db.row_count("SELECT * FROM t") == 0


class TestSelectWhere:
    def test_where_returns_only_matching_rows(self, db_with_users):
        assert db_with_users.row_count("SELECT * FROM users WHERE city = 'Paris'") == 2

    def test_where_excludes_non_matching_rows(self, db_with_users):
        result = db_with_users.q("SELECT * FROM users WHERE city = 'Paris'")
        assert "Bob" not in result

    def test_where_no_match_returns_zero_rows(self, db_with_users):
        assert db_with_users.row_count("SELECT * FROM users WHERE city = 'Tokyo'") == 0

    def test_where_single_match(self, db_with_users):
        result = db_with_users.q("SELECT * FROM users WHERE name = 'Alice'")
        assert "Alice" in result
        assert db_with_users.row_count("SELECT * FROM users WHERE name = 'Alice'") == 1

    def test_where_on_unknown_column_raises(self, db_with_users):
        with pytest.raises(DBError):
            db_with_users.q("SELECT * FROM users WHERE ghost = 'x'")

    def test_where_combined_with_column_projection(self, db_with_users):
        result = db_with_users.q("SELECT name FROM users WHERE city = 'Paris'")
        assert "Alice" in result and "Carol" in result
        assert "id" not in result.splitlines()[0]
