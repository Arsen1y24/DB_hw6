import pytest
from errors import DBError


class TestUpdate:
    def test_update_with_where_changes_matching_row(self, db_with_users):
        db_with_users.q("UPDATE users SET city = 'Berlin' WHERE name = 'Alice'")
        assert db_with_users.row_count("SELECT * FROM users WHERE city = 'Berlin'") == 1

    def test_update_with_where_does_not_affect_other_rows(self, db_with_users):
        db_with_users.q("UPDATE users SET city = 'Berlin' WHERE name = 'Alice'")
        result = db_with_users.q("SELECT * FROM users WHERE name = 'Bob'")
        assert "London" in result

    def test_update_without_where_changes_all_rows(self, db_with_users):
        db_with_users.q("UPDATE users SET city = 'Rome'")
        assert db_with_users.row_count("SELECT * FROM users WHERE city = 'Rome'") == 3

    def test_update_no_match_changes_nothing(self, db_with_users):
        db_with_users.q("UPDATE users SET city = 'X' WHERE name = 'Nobody'")
        assert db_with_users.row_count("SELECT * FROM users") == 3

    def test_update_unknown_column_in_set_raises(self, db_with_users):
        with pytest.raises(DBError):
            db_with_users.q("UPDATE users SET ghost = 'x'")

    def test_update_unknown_column_in_where_raises(self, db_with_users):
        with pytest.raises(DBError):
            db_with_users.q("UPDATE users SET city = 'x' WHERE ghost = 'y'")

    def test_update_nonexistent_table_raises(self, db):
        with pytest.raises(DBError):
            db.q("UPDATE ghost SET a = 'x'")
