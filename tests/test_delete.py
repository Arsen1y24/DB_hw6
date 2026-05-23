import pytest
from errors import DBError


class TestDelete:
    def test_delete_with_where_removes_matching_rows(self, db_with_users):
        db_with_users.q("DELETE FROM users WHERE city = 'Paris'")
        assert db_with_users.row_count("SELECT * FROM users") == 1

    def test_delete_with_where_keeps_non_matching_rows(self, db_with_users):
        db_with_users.q("DELETE FROM users WHERE city = 'Paris'")
        result = db_with_users.q("SELECT * FROM users")
        assert "Bob" in result

    def test_delete_without_where_removes_all_rows(self, db_with_users):
        db_with_users.q("DELETE FROM users")
        assert db_with_users.row_count("SELECT * FROM users") == 0

    def test_delete_no_match_removes_nothing(self, db_with_users):
        db_with_users.q("DELETE FROM users WHERE name = 'Nobody'")
        assert db_with_users.row_count("SELECT * FROM users") == 3

    def test_delete_unknown_column_in_where_raises(self, db_with_users):
        with pytest.raises(DBError):
            db_with_users.q("DELETE FROM users WHERE ghost = 'x'")

    def test_delete_nonexistent_table_raises(self, db):
        with pytest.raises(DBError):
            db.q("DELETE FROM ghost")
