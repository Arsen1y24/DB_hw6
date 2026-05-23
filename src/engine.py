from errors import DBError
from storage import Storage


class Engine:
    def __init__(self, storage: Storage):
        self.storage = storage

    def execute(self, ast: dict) -> str:
        return {
            "CREATE_TABLE": self._create_table,
            "DROP_TABLE":   self._drop_table,
            "INSERT":       self._insert,
            "SELECT":       self._select,
            "UPDATE":       self._update,
            "DELETE":       self._delete,
        }[ast["op"]](ast)

    def _get_table(self, name: str) -> dict:
        t = self.storage.tables.get(name)
        if t is None:
            raise DBError(f"Table '{name}' does not exist")
        t.setdefault("pk", None)
        t.setdefault("pk_seq", 0)
        return t

    def _check_columns(self, names: list[str], columns: list[str], ctx: str):
        for name in names:
            if name not in columns:
                raise DBError(f"Unknown column '{name}' in {ctx}")

    def _resolve(self, atom: dict, row: list, columns: list) -> str:
        if atom["type"] == "LIT":
            return atom["val"]
        if atom["type"] == "COL":
            col = atom["name"]
            if col not in columns:
                raise DBError(f"Unknown column '{col}'")
            return row[columns.index(col)]
        raise DBError(f"Cannot resolve node type '{atom['type']}'")

    def _eval(self, expr: dict, row: list, columns: list) -> bool:
        t = expr["type"]
        if t == "AND":
            return self._eval(expr["left"], row, columns) and self._eval(expr["right"], row, columns)
        if t == "OR":
            return self._eval(expr["left"], row, columns) or self._eval(expr["right"], row, columns)
        if t == "NOT":
            return not self._eval(expr["operand"], row, columns)
        if t == "CMP":
            return self._resolve(expr["left"], row, columns) == self._resolve(expr["right"], row, columns)
        raise DBError(f"Unknown expression node type '{t}'")

    def _matches(self, row: list, columns: list, where: dict | None) -> bool:
        if where is None:
            return True
        return self._eval(where, row, columns)

    def _validate_where(self, expr: dict | None, columns: list):
        if expr is None:
            return
        t = expr["type"]
        if t in ("AND", "OR"):
            self._validate_where(expr["left"], columns)
            self._validate_where(expr["right"], columns)
        elif t == "NOT":
            self._validate_where(expr["operand"], columns)
        elif t == "CMP":
            for side in (expr["left"], expr["right"]):
                if side["type"] == "COL" and side["name"] not in columns:
                    raise DBError(f"Unknown column '{side['name']}' in WHERE")

    def _drop_table(self, ast: dict) -> str:
        name = ast["table"]
        if name not in self.storage.tables:
            raise DBError(f"Table '{name}' does not exist")
        del self.storage.tables[name]
        self.storage.save()
        return f"Table '{name}' dropped."

    def _create_table(self, ast: dict) -> str:
        name = ast["table"]
        if name in self.storage.tables:
            raise DBError(f"Table '{name}' already exists")
        self.storage.tables[name] = {
            "columns": ast["columns"],
            "pk": ast["pk"],
            "pk_seq": 0,
            "rows": [],
        }
        self.storage.save()
        return f"Table '{name}' created."

    def _insert(self, ast: dict) -> str:
        table = self._get_table(ast["table"])
        columns = table["columns"]
        pk_col = table["pk"]

        if ast["columns"] is not None:
            named = ast["columns"]
            self._check_columns(named, columns, "INSERT")
            if len(named) != len(ast["values"]):
                raise DBError(f"Expected {len(named)} value(s), got {len(ast['values'])}")
            row = [None] * len(columns)
            for col, val in zip(named, ast["values"]):
                row[columns.index(col)] = val
            if pk_col and pk_col not in named:
                pk_idx = columns.index(pk_col)
                table["pk_seq"] += 1
                row[pk_idx] = str(table["pk_seq"])
            missing = [columns[i] for i, v in enumerate(row) if v is None]
            if missing:
                raise DBError(f"Missing value(s) for: {', '.join(missing)}")
        else:
            if len(ast["values"]) != len(columns):
                raise DBError(f"Expected {len(columns)} value(s), got {len(ast['values'])}")
            row = list(ast["values"])
            if pk_col:
                pk_idx = columns.index(pk_col)
                try:
                    n = int(row[pk_idx])
                    if n > table["pk_seq"]:
                        table["pk_seq"] = n
                except ValueError:
                    pass

        if pk_col:
            pk_idx = columns.index(pk_col)
            pk_val = row[pk_idx]
            if any(r[pk_idx] == pk_val for r in table["rows"]):
                raise DBError(f"Duplicate value '{pk_val}' for PRIMARY KEY '{pk_col}'")

        table["rows"].append(row)
        self.storage.save()
        return "1 row inserted."

    def _select(self, ast: dict) -> str:
        table = self._get_table(ast["table"])
        columns, rows = table["columns"], table["rows"]

        self._validate_where(ast["where"], columns)

        sel = columns if ast["columns"] == ["*"] else ast["columns"]
        self._check_columns(sel, columns, "SELECT")

        indices = [columns.index(c) for c in sel]
        filtered = [
            [row[i] for i in indices]
            for row in rows
            if self._matches(row, columns, ast["where"])
        ]
        return _format_table(sel, filtered)

    def _update(self, ast: dict) -> str:
        table = self._get_table(ast["table"])
        columns, rows = table["columns"], table["rows"]
        pk_col = table["pk"]

        self._check_columns(list(ast["set"].keys()), columns, "SET")
        self._validate_where(ast["where"], columns)

        if pk_col and pk_col in ast["set"]:
            new_pk = ast["set"][pk_col]
            pk_idx = columns.index(pk_col)
            will_update = [r for r in rows if self._matches(r, columns, ast["where"])]
            wont_update = [r for r in rows if not self._matches(r, columns, ast["where"])]
            if len(will_update) > 1 or any(r[pk_idx] == new_pk for r in wont_update):
                raise DBError(f"Duplicate value '{new_pk}' for PRIMARY KEY '{pk_col}'")

        count = 0
        for row in rows:
            if self._matches(row, columns, ast["where"]):
                for col, val in ast["set"].items():
                    row[columns.index(col)] = val
                count += 1
        self.storage.save()
        return f"{count} row(s) updated."

    def _delete(self, ast: dict) -> str:
        table = self._get_table(ast["table"])
        columns, rows = table["columns"], table["rows"]

        self._validate_where(ast["where"], columns)

        before = len(rows)
        table["rows"] = [r for r in rows if not self._matches(r, columns, ast["where"])]
        self.storage.save()
        return f"{before - len(table['rows'])} row(s) deleted."


def _format_table(columns: list[str], rows: list[list[str]]) -> str:
    widths = [
        max(len(col), max((len(row[i]) for row in rows), default=0))
        for i, col in enumerate(columns)
    ]
    sep    = "-+-".join("-" * w for w in widths)
    header = " | ".join(col.ljust(widths[i]) for i, col in enumerate(columns))
    lines  = [header, sep]
    for row in rows:
        lines.append(" | ".join(row[i].ljust(widths[i]) for i in range(len(columns))))
    n = len(rows)
    lines.append(f"({n} row{'s' if n != 1 else ''})")
    return "\n".join(lines)
