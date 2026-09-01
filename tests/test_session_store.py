# tests/test_session_store.py

from services.session_store import SessionStore


def test_load_returns_none_when_no_file(tmp_path):
    store = SessionStore(file_path=str(tmp_path / "session.json"))
    assert store.load() is None


def test_save_and_load_round_trip(tmp_path):
    store = SessionStore(file_path=str(tmp_path / "session.json"))

    session_data = {
        "template_file": "/tenders/Template.xlsx",
        "benchmark_file": "/tenders/Benchmark.xlsx",
        "supplier_files": ["/tenders/A.xlsx", "/tenders/B.xlsx"],
        "output_folder": "/tenders/reports",
    }

    store.save(session_data)
    loaded = store.load()

    assert loaded == session_data


def test_load_returns_none_on_corrupt_file(tmp_path):
    file_path = tmp_path / "session.json"
    file_path.write_text("{not valid")

    store = SessionStore(file_path=str(file_path))
    assert store.load() is None


def test_clear_removes_the_file(tmp_path):
    file_path = tmp_path / "session.json"
    store = SessionStore(file_path=str(file_path))

    store.save({"template_file": "a.xlsx"})
    assert file_path.exists()

    store.clear()
    assert not file_path.exists()
