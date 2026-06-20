import logging
import os
from typing import List

import pandas as pd


logger = logging.getLogger(__name__)


class BatchProcessor:
    ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
    ADDRESS_COLUMN_VARIANTS = ["address", "адрес", "Address", "Адрес", "addr"]

    def parse_file(self, file_path: str) -> List[str]:
        """Parse uploaded Excel/CSV and extract a list of addresses."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}")

        if ext == ".csv":
            df = pd.read_csv(file_path, encoding="utf-8-sig")
        else:
            df = pd.read_excel(file_path)

        # Find the address column
        address_col = None
        for variant in self.ADDRESS_COLUMN_VARIANTS:
            if variant in df.columns:
                address_col = variant
                break

        if address_col is None:
            raise ValueError(
                f"No address column found. Expected one of: {self.ADDRESS_COLUMN_VARIANTS}. "
                f"Found: {list(df.columns)}"
            )

        addresses = df[address_col].dropna().astype(str).str.strip().tolist()
        addresses = [a for a in addresses if len(a) > 5]
        return addresses

    def determine_priority(self, score: float) -> str:
        if score >= 75:
            return "high"
        elif score >= 50:
            return "medium"
        return "low"
