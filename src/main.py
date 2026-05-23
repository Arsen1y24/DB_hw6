import sys

from errors import DBError
from storage import Storage
from parser import parse
from engine import Engine


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "db.json"
    engine = Engine(Storage(path))

    print(f"Simple DBMS  |  {path}  |  type EXIT to quit\n")
    while True:
        try:
            line = input("db> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.upper() == "EXIT":
            break
        try:
            print(engine.execute(parse(line)))
        except DBError as e:
            print(f"ERROR: {e}")


if __name__ == "__main__":
    main()
