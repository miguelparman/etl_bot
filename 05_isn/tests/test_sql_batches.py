from src.database.connection import split_batches


def test_split_batches_separates_on_go_lines():
    script = """
SELECT 1
GO
SELECT 2
GO
SELECT 3
"""
    batches = split_batches(script)
    assert len(batches) == 3
    assert batches[0] == "SELECT 1"
    assert batches[1] == "SELECT 2"
    assert batches[2] == "SELECT 3"


def test_split_batches_without_go_returns_single_batch():
    script = "SELECT 1"
    assert split_batches(script) == ["SELECT 1"]


def test_split_batches_ignores_go_inside_other_text():
    # "GO" no debe partir el lote si no esta sola en su propia linea
    script = "SELECT 'GOOD' AS x"
    assert split_batches(script) == ["SELECT 'GOOD' AS x"]
