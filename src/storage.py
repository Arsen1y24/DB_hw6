import json
import os
import struct

from errors import DBError

PAGE_SIZE = 4096
HDR_SIZE = 8    # num_slots (2) + free_end (2) + reserved (4)
SLOT_SIZE = 4   # offset (2) + length (2)


class PagedStorage:
    def __init__(self, db_dir: str):
        self.db_dir = db_dir
        os.makedirs(db_dir, exist_ok=True)
        self._cat = os.path.join(db_dir, "catalog.json")
        if os.path.exists(self._cat):
            with open(self._cat) as f:
                self._catalog = json.load(f)
        else:
            self._catalog = {"tables": {}}

    @property
    def tables(self) -> dict:
        return self._catalog["tables"]

    def _dat(self, name: str) -> str:
        return os.path.join(self.db_dir, name + ".dat")

    def save_catalog(self):
        tmp = self._cat + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._catalog, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self._cat)

    def drop_table_data(self, name: str):
        path = self._dat(name)
        if os.path.exists(path):
            os.remove(path)

    @staticmethod
    def _new_page() -> bytearray:
        page = bytearray(PAGE_SIZE)
        struct.pack_into(">HH", page, 0, 0, PAGE_SIZE)
        return page

    @staticmethod
    def _read_hdr(page: bytearray) -> tuple[int, int]:
        return struct.unpack_from(">HH", page, 0)

    @staticmethod
    def _write_hdr(page: bytearray, n: int, free_end: int):
        struct.pack_into(">HH", page, 0, n, free_end)

    @staticmethod
    def _read_slot(page: bytearray, s: int) -> tuple[int, int]:
        return struct.unpack_from(">HH", page, HDR_SIZE + s * SLOT_SIZE)

    @staticmethod
    def _write_slot(page: bytearray, s: int, offset: int, length: int):
        struct.pack_into(">HH", page, HDR_SIZE + s * SLOT_SIZE, offset, length)

    @staticmethod
    def _insert_into_page(page: bytearray, data: bytes) -> bool:
        n, free_end = PagedStorage._read_hdr(page)
        needed = len(data) + SLOT_SIZE
        if free_end - (HDR_SIZE + n * SLOT_SIZE) < needed:
            return False
        free_end -= len(data)
        page[free_end: free_end + len(data)] = data
        PagedStorage._write_slot(page, n, free_end, len(data))
        PagedStorage._write_hdr(page, n + 1, free_end)
        return True

    def _page_count(self, name: str) -> int:
        path = self._dat(name)
        if not os.path.exists(path):
            return 0
        return os.path.getsize(path) // PAGE_SIZE

    def _load_page(self, f, pid: int) -> bytearray:
        f.seek(pid * PAGE_SIZE)
        raw = f.read(PAGE_SIZE)
        raw += b"\x00" * (PAGE_SIZE - len(raw))
        return bytearray(raw)

    def _save_page(self, f, pid: int, page: bytearray):
        f.seek(pid * PAGE_SIZE)
        f.write(bytes(page))
        f.flush()
        os.fsync(f.fileno())

    def read_all_tuples(self, name: str) -> list[tuple[int, int, bytes]]:
        path = self._dat(name)
        if not os.path.exists(path):
            return []
        result = []
        with open(path, "rb") as f:
            for pid in range(self._page_count(name)):
                page = self._load_page(f, pid)
                n, _ = self._read_hdr(page)
                for sid in range(n):
                    off, length = self._read_slot(page, sid)
                    if length == 0:
                        continue
                    result.append((pid, sid, bytes(page[off: off + length])))
        return result

    def append_tuple(self, name: str, data: bytes):
        if len(data) + SLOT_SIZE + HDR_SIZE > PAGE_SIZE:
            raise DBError(f"Row too large ({len(data)} bytes)")
        path = self._dat(name)
        pc = self._page_count(name)
        mode = "r+b" if os.path.exists(path) else "w+b"
        with open(path, mode) as f:
            if pc > 0:
                page = self._load_page(f, pc - 1)
                if self._insert_into_page(page, data):
                    self._save_page(f, pc - 1, page)
                    return
            page = self._new_page()
            self._insert_into_page(page, data)
            self._save_page(f, pc, page)

    def delete_tuple(self, name: str, pid: int, sid: int):
        with open(self._dat(name), "r+b") as f:
            page = self._load_page(f, pid)
            off, _ = self._read_slot(page, sid)
            self._write_slot(page, sid, off, 0)
            self._save_page(f, pid, page)

    def update_tuple(self, name: str, pid: int, sid: int, new_data: bytes):
        with open(self._dat(name), "r+b") as f:
            page = self._load_page(f, pid)
            off, old_len = self._read_slot(page, sid)
            if len(new_data) <= old_len:
                page[off: off + len(new_data)] = new_data
                self._write_slot(page, sid, off, len(new_data))
                self._save_page(f, pid, page)
                return
        self.delete_tuple(name, pid, sid)
        self.append_tuple(name, new_data)

    def truncate_table(self, name: str):
        path = self._dat(name)
        if os.path.exists(path):
            open(path, "wb").close()
