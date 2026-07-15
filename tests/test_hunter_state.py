import json
from laptopfinder.runners.legacy.hunter.state import load_seen, save_seen, write_jsonl

def test_load_seen_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("laptopfinder.runners.legacy.hunter.state.SEEN_PATH", tmp_path / "seen_items.json")
    assert load_seen() == set()

def test_save_and_load_seen(tmp_path, monkeypatch):
    p = tmp_path / "seen_items.json"
    monkeypatch.setattr("laptopfinder.runners.legacy.hunter.state.SEEN_PATH", p)
    save_seen({"item1", "item2"})
    assert p.exists()
    assert load_seen() == {"item1", "item2"}

def test_write_jsonl(tmp_path):
    p = tmp_path / "out.jsonl"
    write_jsonl(p, [{"a": 1}, {"b": 2}])
    content = p.read_text().splitlines()
    assert len(content) == 2
    assert json.loads(content[0]) == {"a": 1}
    assert json.loads(content[1]) == {"b": 2}
