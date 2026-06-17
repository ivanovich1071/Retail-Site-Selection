import os
import tempfile
import pytest
import pandas as pd
from backend.app.services.batch_processor import BatchProcessor


@pytest.fixture
def processor():
    return BatchProcessor()


def make_excel(addresses: list, col: str = "address") -> str:
    df = pd.DataFrame({col: addresses})
    path = tempfile.mktemp(suffix=".xlsx")
    df.to_excel(path, index=False)
    return path


def test_parse_excel_standard_column(processor):
    path = make_excel(["ул. Ленина 1, Минск", "пр. Победителей 5"])
    result = processor.parse_file(path)
    assert len(result) == 2
    os.unlink(path)


def test_parse_excel_russian_column(processor):
    path = make_excel(["ул. Ленина 1", "пр. Мира 2"], col="адрес")
    result = processor.parse_file(path)
    assert len(result) == 2
    os.unlink(path)


def test_parse_unsupported_extension(processor):
    with pytest.raises(ValueError, match="Unsupported"):
        processor.parse_file("file.json")


def test_parse_missing_column(processor):
    df = pd.DataFrame({"city": ["Минск"]})
    path = tempfile.mktemp(suffix=".xlsx")
    df.to_excel(path, index=False)
    with pytest.raises(ValueError, match="No address column"):
        processor.parse_file(path)
    os.unlink(path)


def test_priority_thresholds(processor):
    assert processor.determine_priority(80) == "high"
    assert processor.determine_priority(60) == "medium"
    assert processor.determine_priority(30) == "low"
