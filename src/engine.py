from datatypes import coerce, deserialize_row, display, serialize_row
from errors import DBError
from storage import PagedStorage


def _col_names(table):
    return [c["name"] for c in table["columns"]]

def _col_types(table):
    return [c["type"] for c in table["columns"]]

def _type_map(table):
    return {c["name"]: c["type"] for c in table["columns"]}


class Engine:
    def __init__(self, storage: PagedStorage):
        self.storage = storage

    def execute(self, ast: dict) -> str:
        ops = {
            "CREATE_TABLE": self._create_table,
            "DROP_TABLE": self._drop_table,
            "INSERT": self._insert,
            "SELECT": self._select,
            "UPDATE": self._update,
            "DELETE": self._delete,
        }
        return ops[ast["op"]](ast)

    def _get_table(self, name: str) -> dict:
        t = self.storage.tables.get(name)
        if t is None:
            raise DBError(f"Table '{name}' does not exist")
        t.setdefault("pk", None)
        t.setdefault("pk_seq", 0)
        return t

    def _resolve(self, atom, row, cols):
        if atom["type"] == "LIT":
            return atom["val"]
        if atom["type"] == "COL":
            if atom["name"] not in cols:
                raise DBError(f"Unknown column '{atom['name']}'")
            return row[cols.index(atom["name"])]
        raise DBError(f"Unknown node type '{atom['type']}'")

    def _eval(self, expr, row, cols, types):
        t = expr["type"]
        if t == "AND":
            return self._eval(expr["left"], row, cols, types) and self._eval(expr["right"], row, cols, types)
        if t == "OR":
            return self._eval(expr["left"], row, cols, types) or self._eval(expr["right"], row, cols, types)
        if t == "NOT":
            return not self._eval(expr["operand"], row, cols, types)
        if t == "CMP":
            lv = self._resolve(expr["left"], row, cols)
            rv = self._resolve(expr["right"], row, cols)
            if expr["left"]["type"] == "COL" and expr["right"]["type"] == "LIT":
                rv = coerce(str(rv), types.get(expr["left"]["name"], "TEXT"))
            elif expr["right"]["type"] == "COL" and expr["left"]["type"] == "LIT":
                lv = coerce(str(lv), types.get(expr["right"]["name"], "TEXT"))
            if expr["op"] == "=":
                return lv == rv
            raise DBError(f"Unknown operator '{expr['op']}'")
        raise DBError(f"Unknown expression type '{t}'")

    def _matches(self, row, cols, types, where):
        if where is None:
            return True
        return self._eval(where, row, cols, types)

    def _check_where_cols(self, expr, cols):
        if expr is None:
            return
        t = expr["type"]
        if t in ("AND", "OR"):
            self._check_where_cols(expr["left"], cols)
            self._check_where_cols(expr["right"], cols)
        elif t == "NOT":
            self._check_where_cols(expr["operand"], cols)
        elif t == "CMP":
            for side in (expr["left"], expr["right"]):
                if side["type"] == "COL" and side["name"] not in cols:
                    raise DBError(f"Unknown column '{side['name']}' in WHERE")

    def _create_table(self, ast: dict) -> str:
        name = ast["table"]
        if name in self.storage.tables:
            raise DBError(f"Table '{name}' already exists")
        self.storage.tables[name] = {
            "columns": ast["columns"],
            "pk": ast["pk"],
            "pk_seq": 0,
        }
        self.storage.save_catalog()
        return f"Table '{name}' created."

    def _drop_table(self, ast: dict) -> str:
        name = ast["table"]
        if name not in self.storage.tables:
            raise DBError(f"Table '{name}' does not exist")
        del self.storage.tables[name]
        self.storage.drop_table_data(name)
        self.storage.save_catalog()
        return f"Table '{name}' dropped."

    def _insert(self, ast: dict) -> str:
        table = self._get_table(ast["table"])
        cols = _col_names(table)
        types = _col_types(table)
        pk_col = table["pk"]

        if ast["columns"] is not None:
            named = ast["columns"]
            for c in named:
                if c not in cols:
                    raise DBError(f"Unknown column '{c}' in INSERT")
            if len(named) != len(ast["values"]):
                raise DBError(f"Expected {len(named)} value(s), got {len(ast['values'])}")
            row: list[int | float | str | bool | None] = [None] * len(cols)
            for col, val in zip(named, ast["values"]):
                idx = cols.index(col)
                row[idx] = coerce(val, types[idx])
            if pk_col and pk_col not in named:
                pk_idx = cols.index(pk_col)
                table["pk_seq"] += 1
                row[pk_idx] = table["pk_seq"] if types[pk_idx] == "INTEGER" else str(table["pk_seq"])
            missing = [cols[i] for i, v in enumerate(row) if v is None]
            if missing:
                raise DBError(f"Missing values for: {', '.join(missing)}")
        else:
            if len(ast["values"]) != len(cols):
                raise DBError(f"Expected {len(cols)} value(s), got {len(ast['values'])}")
            row = [coerce(v, t) for v, t in zip(ast["values"], types)]
            if pk_col:
                pk_idx = cols.index(pk_col)
                pk_val = row[pk_idx]
                seq_val = pk_val if types[pk_idx] == "INTEGER" else _try_int(pk_val)
                if seq_val is not None and seq_val > table["pk_seq"]:
                    table["pk_seq"] = seq_val

        if pk_col:
            pk_idx = cols.index(pk_col)
            pk_val = row[pk_idx]
            for _, _, raw in self.storage.read_all_tuples(ast["table"]):
                if deserialize_row(raw, types)[pk_idx] == pk_val:
                    raise DBError(f"Duplicate PRIMARY KEY value '{pk_val}'")

        self.storage.append_tuple(ast["table"], serialize_row(row, types))
        self.storage.save_catalog()
        return "1 row inserted."

    def _select(self, ast: dict) -> str:
        table = self._get_table(ast["table"])
        cols = _col_names(table)
        types = _col_types(table)
        tmap = _type_map(table)

        self._check_where_cols(ast["where"], cols)

        sel = cols if ast["columns"] == ["*"] else ast["columns"]
        for c in sel:
            if c not in cols:
                raise DBError(f"Unknown column '{c}' in SELECT")

        indices = [cols.index(c) for c in sel]
        sel_types = [types[i] for i in indices]

        rows = []
        for _, _, raw in self.storage.read_all_tuples(ast["table"]):
            row = deserialize_row(raw, types)
            if self._matches(row, cols, tmap, ast["where"]):
                rows.append([row[i] for i in indices])

        return _format_table(sel, sel_types, rows)

    def _update(self, ast: dict) -> str:
        table = self._get_table(ast["table"])
        cols = _col_names(table)
        types = _col_types(table)
        tmap = _type_map(table)
        pk_col = table["pk"]

        for c in ast["set"]:
            if c not in cols:
                raise DBError(f"Unknown column '{c}' in SET")
        self._check_where_cols(ast["where"], cols)

        set_typed = {col: coerce(val, tmap[col]) for col, val in ast["set"].items()}

        all_rows = [
            (pid, sid, deserialize_row(raw, types))
            for pid, sid, raw in self.storage.read_all_tuples(ast["table"])
        ]

        if pk_col and pk_col in set_typed:
            new_pk = set_typed[pk_col]
            pk_idx = cols.index(pk_col)
            matching = sum(1 for _, _, row in all_rows if self._matches(row, cols, tmap, ast["where"]))
            other_pks = {row[pk_idx] for _, _, row in all_rows if not self._matches(row, cols, tmap, ast["where"])}
            if matching > 1 or new_pk in other_pks:
                raise DBError(f"Duplicate PRIMARY KEY value '{new_pk}'")

        count = 0
        for pid, sid, row in all_rows:
            if self._matches(row, cols, tmap, ast["where"]):
                new_row = list(row)
                for col, val in set_typed.items():
                    new_row[cols.index(col)] = val
                self.storage.update_tuple(ast["table"], pid, sid, serialize_row(new_row, types))
                count += 1

        self.storage.save_catalog()
        return f"{count} row(s) updated."

    def _delete(self, ast: dict) -> str:
        table = self._get_table(ast["table"])
        cols = _col_names(table)
        types = _col_types(table)
        tmap = _type_map(table)

        self._check_where_cols(ast["where"], cols)

        if ast["where"] is None:
            count = len(self.storage.read_all_tuples(ast["table"]))
            self.storage.truncate_table(ast["table"])
            return f"{count} row(s) deleted."

        count = 0
        for pid, sid, raw in self.storage.read_all_tuples(ast["table"]):
            row = deserialize_row(raw, types)
            if self._matches(row, cols, tmap, ast["where"]):
                self.storage.delete_tuple(ast["table"], pid, sid)
                count += 1
        return f"{count} row(s) deleted."


def _try_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _format_table(columns, types, rows):
    str_rows = [[display(v, t) for v, t in zip(row, types)] for row in rows]
    widths = [
        max(len(col), max((len(str_rows[j][i]) for j in range(len(str_rows))), default=0))
        for i, col in enumerate(columns)
    ]
    sep = "-+-".join("-" * w for w in widths)
    header = " | ".join(col.ljust(widths[i]) for i, col in enumerate(columns))
    lines = [header, sep]
    for row in str_rows:
        lines.append(" | ".join(row[i].ljust(widths[i]) for i in range(len(columns))))
    n = len(rows)
    lines.append(f"({n} row{'s' if n != 1 else ''})")
    return "\n".join(lines)
