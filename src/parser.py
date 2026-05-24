import re

from errors import DBError


def parse(sql: str) -> dict:
    sql = sql.strip()
    if not sql:
        raise DBError("Empty query")
    keyword = sql.split()[0].upper()
    dispatch = {
        "CREATE": _parse_create_table,
        "DROP":   _parse_drop_table,
        "INSERT": _parse_insert,
        "SELECT": _parse_select,
        "UPDATE": _parse_update,
        "DELETE": _parse_delete,
    }
    if keyword not in dispatch:
        raise DBError(f"Unknown command: {keyword!r}")
    return dispatch[keyword](sql)


def _parse_value_list(s: str) -> list[str]:
    values, i = [], 0
    s = s.strip()
    while i < len(s):
        while i < len(s) and s[i] in " \t,":
            i += 1
        if i >= len(s):
            break
        if s[i] in ("'", '"'):
            q = s[i]
            i += 1
            start = i
            while i < len(s) and s[i] != q:
                i += 1
            values.append(s[start:i])
            i += 1
        else:
            start = i
            while i < len(s) and s[i] not in " \t,":
                i += 1
            values.append(s[start:i])
    return values


def _split_by_comma_outside_quotes(s: str) -> list[str]:
    parts, current, in_quote = [], [], False
    for ch in s:
        if ch == "'":
            in_quote = not in_quote
            current.append(ch)
        elif ch == "," and not in_quote:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


def _tokenize_expr(s: str) -> list[tuple[str, str]]:
    tokens, i = [], 0
    while i < len(s):
        c = s[i]
        if c in " \t\n\r":
            i += 1
        elif c in ("'", '"'):
            q = c
            i += 1
            start = i
            while i < len(s) and s[i] != q:
                i += 1
            if i >= len(s):
                raise DBError("Unterminated string literal in WHERE")
            tokens.append(("LIT", s[start:i]))
            i += 1
        elif c == "=":
            tokens.append(("OP", c))
            i += 1
        elif c == "(":
            tokens.append(("LPAREN", "("))
            i += 1
        elif c == ")":
            tokens.append(("RPAREN", ")"))
            i += 1
        elif c.isdigit() or (c == "-" and i + 1 < len(s) and s[i + 1].isdigit()):
            start = i
            if c == "-":
                i += 1
            while i < len(s) and (s[i].isdigit() or s[i] == "."):
                i += 1
            tokens.append(("NUM", s[start:i]))
        elif c.isalpha() or c == "_":
            start = i
            while i < len(s) and (s[i].isalnum() or s[i] == "_"):
                i += 1
            tokens.append(("WORD", s[start:i]))
        else:
            raise DBError(f"Unexpected character in WHERE: {c!r}")
    return tokens


class _ExprParser:
    def __init__(self, tokens: list):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> tuple | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self) -> tuple:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _is(self, *words: str) -> bool:
        tok = self.peek()
        return (
            tok is not None
            and tok[0] == "WORD"
            and tok[1].upper() in {w.upper() for w in words}
        )

    def parse(self) -> dict:
        expr = self._or()
        if self.pos < len(self.tokens):
            tok = self.peek()
            if tok is None:
                raise DBError("Unexpected end of WHERE expression")
            raise DBError(f"Unexpected token in WHERE: {tok[1]!r}")
        return expr

    def _or(self) -> dict:
        left = self._and()
        while self._is("OR"):
            self.consume()
            left = {"type": "OR", "left": left, "right": self._and()}
        return left

    def _and(self) -> dict:
        left = self._not()
        while self._is("AND"):
            self.consume()
            left = {"type": "AND", "left": left, "right": self._not()}
        return left

    def _not(self) -> dict:
        if self._is("NOT"):
            self.consume()
            return {"type": "NOT", "operand": self._not()}
        return self._cmp()

    def _cmp(self) -> dict:
        left = self._atom()
        tok = self.peek()
        if tok is not None and tok[0] == "OP":
            op = self.consume()[1]
            return {"type": "CMP", "op": op, "left": left, "right": self._atom()}
        return left

    def _atom(self) -> dict:
        tok = self.peek()
        if tok is None:
            raise DBError("Unexpected end of WHERE expression")
        ttype, tval = tok
        if ttype == "LPAREN":
            self.consume()
            expr = self._or()
            tok = self.peek()
            if tok is None or tok[0] != "RPAREN":
                raise DBError("Missing ')' in WHERE expression")
            self.consume()
            return expr
        if ttype == "LIT":
            self.consume()
            return {"type": "LIT", "val": tval}
        if ttype == "NUM":
            self.consume()
            return {"type": "LIT", "val": tval}
        if ttype == "WORD":
            if tval.upper() in ("TRUE", "FALSE"):
                self.consume()
                return {"type": "LIT", "val": tval.upper()}
            if tval.upper() in ("AND", "OR", "NOT"):
                raise DBError(f"Unexpected keyword {tval!r} in WHERE expression")
            self.consume()
            return {"type": "COL", "name": tval}
        raise DBError(f"Unexpected token {tval!r} in WHERE expression")


def _parse_where(s: str) -> dict | None:
    s = s.strip() if s else ""
    if not s:
        return None
    return _ExprParser(_tokenize_expr(s)).parse()


def _parse_drop_table(sql: str) -> dict:
    m = re.match(r"DROP\s+TABLE\s+(\w+)\s*;?\s*$", sql, re.IGNORECASE)
    if not m:
        raise DBError("Syntax: DROP TABLE name")
    return {"op": "DROP_TABLE", "table": m.group(1)}


def _parse_create_table(sql: str) -> dict:
    m = re.match(
        r"CREATE\s+TABLE\s+(\w+)\s*\((.+)\)\s*;?\s*$", sql, re.IGNORECASE | re.DOTALL
    )
    if not m:
        raise DBError("Syntax: CREATE TABLE name (col TYPE [PRIMARY KEY], ...)")
    table = m.group(1)
    pk = None
    columns = []
    _TYPES = "INTEGER|REAL|TEXT|BOOLEAN"
    for part in _split_by_comma_outside_quotes(m.group(2)):
        part = part.strip()
        # col TYPE PRIMARY KEY
        m2 = re.match(rf"(\w+)\s+({_TYPES})\s+PRIMARY\s+KEY\s*$", part, re.IGNORECASE)
        if m2:
            if pk is not None:
                raise DBError("Only one PRIMARY KEY allowed")
            pk = m2.group(1)
            columns.append({"name": m2.group(1), "type": m2.group(2).upper()})
            continue
        # col PRIMARY KEY  (type defaults to TEXT)
        m2 = re.match(r"(\w+)\s+PRIMARY\s+KEY\s*$", part, re.IGNORECASE)
        if m2:
            if pk is not None:
                raise DBError("Only one PRIMARY KEY allowed")
            pk = m2.group(1)
            columns.append({"name": m2.group(1), "type": "TEXT"})
            continue
        # col TYPE
        m2 = re.match(rf"(\w+)\s+({_TYPES})\s*$", part, re.IGNORECASE)
        if m2:
            columns.append({"name": m2.group(1), "type": m2.group(2).upper()})
            continue
        # bare col  (defaults to TEXT for backward compatibility)
        m2 = re.match(r"(\w+)\s*$", part)
        if m2:
            columns.append({"name": m2.group(1), "type": "TEXT"})
            continue
        raise DBError(f"Invalid column definition: {part!r}")
    if not columns:
        raise DBError("No columns defined")
    return {"op": "CREATE_TABLE", "table": table, "columns": columns, "pk": pk}


def _parse_insert(sql: str) -> dict:
    m = re.match(
        r"INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)\s+VALUES\s*\((.+)\)\s*;?\s*$",
        sql, re.IGNORECASE | re.DOTALL,
    )
    if m:
        return {
            "op": "INSERT",
            "table": m.group(1),
            "columns": [c.strip() for c in m.group(2).split(",")],
            "values": _parse_value_list(m.group(3)),
        }
    m = re.match(
        r"INSERT\s+INTO\s+(\w+)\s+VALUES\s*\((.+)\)\s*;?\s*$",
        sql, re.IGNORECASE | re.DOTALL,
    )
    if m:
        return {
            "op": "INSERT",
            "table": m.group(1),
            "columns": None,
            "values": _parse_value_list(m.group(2)),
        }
    raise DBError("Syntax: INSERT INTO table [(col1, col2)] VALUES ('v1', 'v2', ...)")


def _parse_select(sql: str) -> dict:
    m = re.match(
        r"SELECT\s+(.+?)\s+FROM\s+(\w+)(?:\s+WHERE\s+(.+?))?\s*;?\s*$",
        sql, re.IGNORECASE | re.DOTALL,
    )
    if not m:
        raise DBError("Syntax: SELECT col1, col2 FROM table [WHERE ...]")
    cols_str = m.group(1).strip()
    columns = ["*"] if cols_str == "*" else [c.strip() for c in cols_str.split(",")]
    return {
        "op": "SELECT",
        "table": m.group(2),
        "columns": columns,
        "where": _parse_where(m.group(3)),
    }


def _parse_update(sql: str) -> dict:
    m = re.match(
        r"UPDATE\s+(\w+)\s+SET\s+(.+?)(?:\s+WHERE\s+(.+?))?\s*;?\s*$",
        sql, re.IGNORECASE | re.DOTALL,
    )
    if not m:
        raise DBError("Syntax: UPDATE table SET col='val' [WHERE ...]")

    updates = {}
    for assignment in _split_by_comma_outside_quotes(m.group(2)):
        a = re.fullmatch(r'(\w+)\s*=\s*[\'"]([^\'"]*)[\'"]', assignment.strip())
        if not a:
            a = re.fullmatch(r"(\w+)\s*=\s*(\S+)", assignment.strip())
        if not a:
            raise DBError(f"Invalid SET assignment: {assignment.strip()!r}")
        updates[a.group(1)] = a.group(2)

    return {
        "op": "UPDATE",
        "table": m.group(1),
        "set": updates,
        "where": _parse_where(m.group(3)),
    }


def _parse_delete(sql: str) -> dict:
    m = re.match(
        r"DELETE\s+FROM\s+(\w+)(?:\s+WHERE\s+(.+?))?\s*;?\s*$",
        sql, re.IGNORECASE | re.DOTALL,
    )
    if not m:
        raise DBError("Syntax: DELETE FROM table [WHERE ...]")
    return {
        "op": "DELETE",
        "table": m.group(1),
        "where": _parse_where(m.group(2)),
    }
