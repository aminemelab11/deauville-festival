from __future__ import annotations

import json
from abc import ABC, abstractmethod
from json import JSONDecodeError
from pathlib import Path
from tempfile import NamedTemporaryFile

from deauville.festival import DataError, Festival, FestivalError, festival_from_data


class Storage(ABC):
    @abstractmethod
    def load(self) -> Festival:
        raise NotImplementedError

    @abstractmethod
    def save(self, festival: Festival) -> None:
        raise NotImplementedError


class JsonFileStorage(Storage):
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> Festival:
        try:
            with self.path.open(encoding="utf-8") as file:
                data = json.load(file)
            return festival_from_data(data)
        except JSONDecodeError as error:
            raise DataError("The festival data file contains invalid JSON.") from error
        except FestivalError as error:
            raise DataError(f"The festival data is invalid: {error}") from error
        except (KeyError, TypeError, ValueError) as error:
            raise DataError("The festival data has an invalid structure.") from error

    def save(self, festival: Festival) -> None:
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.path.parent, delete=False
            ) as file:
                temporary_path = Path(file.name)
                json.dump(festival.to_data(), file, ensure_ascii=False, indent=2)
                file.write("\n")
            temporary_path.replace(self.path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)


class MemoryStorage(Storage):
    def __init__(self, festival: Festival) -> None:
        self.festival = festival

    def load(self) -> Festival:
        return self.festival

    def save(self, festival: Festival) -> None:
        self.festival = festival
