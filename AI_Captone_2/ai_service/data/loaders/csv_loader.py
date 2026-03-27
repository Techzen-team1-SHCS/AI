from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd


@dataclass(frozen=True)
class CsvLoadConfig:
    path: Path
    usecols: Optional[Iterable[str]] = None
    encoding: Optional[str] = None


class CsvLoader:
    def load(self, config: CsvLoadConfig) -> pd.DataFrame:
        return pd.read_csv(
            config.path,
            usecols=list(config.usecols) if config.usecols is not None else None,
            encoding=config.encoding,
        )

