import json
import os


class Storage:  
    def __init__(self, path: str):
        self.path = path
        if os.path.exists(path):
            with open(path) as f:
                self._data = json.load(f)
        else:
            self._data = {"tables": {}}

    @property
    def tables(self) -> dict:
        return self._data["tables"]

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)
