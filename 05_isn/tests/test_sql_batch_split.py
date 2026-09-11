from db import split_batches


def test_split_batches_sin_go_devuelve_un_solo_batch():
    assert split_batches("SELECT 1") == ["SELECT 1"]


def test_split_batches_separa_por_linea_go():
    sql = "SELECT 1\nGO\nSELECT 2\nGO\n"
    assert split_batches(sql) == ["SELECT 1", "SELECT 2"]


def test_split_batches_ignora_go_dentro_de_una_cadena_o_comentario():
    # "GO" solo cuenta como separador si está solo en su línea (como hace sqlcmd/SSMS).
    sql = "SELECT 'GO to market'\nGO\nSELECT 2"
    batches = split_batches(sql)
    assert len(batches) == 2
    assert "GO to market" in batches[0]


def test_split_batches_tolera_espacios_alrededor_de_go():
    sql = "SELECT 1\n   GO   \nSELECT 2"
    assert split_batches(sql) == ["SELECT 1", "SELECT 2"]


def test_split_batches_no_case_sensitive():
    sql = "SELECT 1\ngo\nSELECT 2"
    assert split_batches(sql) == ["SELECT 1", "SELECT 2"]
