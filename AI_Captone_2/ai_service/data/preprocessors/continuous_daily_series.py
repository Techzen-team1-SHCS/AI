from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ContinuousSeriesConfig:
    fill_value: float = 0.0


class ContinuousDailySeriesPreprocessor:
    def make_continuous(self, df_ds_y: pd.DataFrame, config: ContinuousSeriesConfig) -> pd.DataFrame:
        if "ds" not in df_ds_y.columns or "y" not in df_ds_y.columns:
            raise ValueError("Expected columns: ds, y")

        df = df_ds_y.copy()
        df["ds"] = pd.to_datetime(df["ds"])
        df = df.sort_values("ds").reset_index(drop=True)

        if df.empty:
            return df

        full_range = pd.date_range(start=df["ds"].min(), end=df["ds"].max(), freq="D")
        out = (
            df.set_index("ds")
            .reindex(full_range)
            .rename_axis("ds")
            .reset_index()
        )
        out["y"] = out["y"].fillna(config.fill_value).astype("float64")
        return out

