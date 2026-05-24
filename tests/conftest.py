import pytest

from errors import DBError
from storage import PagedStorage
from parser import parse
from engine import Engine


class DBMS:
    def __init__(self, path):
        self._engine = Engine(PagedStorage(path))
        self.path = path

    def q(self, sql: str) -> str:
        return self._engine.execute(parse(sql))

    def rows(self, sql: str) -> list[list[str]]:
        lines = self.q(sql).splitlines()
        return [
            [cell.strip() for cell in line.split("|")]
            for line in lines[2:-1]
        ]

    def row_count(self, sql: str) -> int:
        last = self.q(sql).splitlines()[-1]
        return int(last.strip("()").split()[0])


@pytest.fixture
def db(tmp_path):
    return DBMS(str(tmp_path / "db"))

@pytest.fixture
def db_with_users(db):
    db.q("CREATE TABLE users (id, name, city)")
    db.q("INSERT INTO users VALUES ('1', 'Alice', 'Paris')")
    db.q("INSERT INTO users VALUES ('2', 'Bob',   'London')")
    db.q("INSERT INTO users VALUES ('3', 'Carol', 'Paris')")
    return db
