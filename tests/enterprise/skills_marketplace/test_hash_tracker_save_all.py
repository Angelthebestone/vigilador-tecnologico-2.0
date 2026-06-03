"""T049: Verify HashTracker save_all batch write."""
import tempfile
import json
from pathlib import Path

from vigilancia_multiagente.enterprise.skills_marketplace.hash_tracker import HashTracker


def test_update_only_modifies_memory():
    """update() only modifies memory, not disk."""
    with tempfile.TemporaryDirectory() as tmp:
        registry_path = Path(tmp) / "hashes.json"
        tracker = HashTracker(registry_path)
        tracker.update("skill-1", "hash-1")
        assert tracker.get("skill-1") == "hash-1"
        assert not registry_path.exists()  # File should not exist yet


def test_save_all_writes_to_disk():
    """save_all() batch writes all hashes to disk."""
    with tempfile.TemporaryDirectory() as tmp:
        registry_path = Path(tmp) / "hashes.json"
        tracker = HashTracker(registry_path)
        tracker.update("skill-1", "hash-1")
        tracker.update("skill-2", "hash-2")
        tracker.save_all()
        assert registry_path.exists()
        data = json.loads(registry_path.read_text())
        assert data == {"skill-1": "hash-1", "skill-2": "hash-2"}


def test_load_from_disk():
    """HashTracker loads existing hashes from disk on init."""
    with tempfile.TemporaryDirectory() as tmp:
        registry_path = Path(tmp) / "hashes.json"
        registry_path.write_text(json.dumps({"skill-1": "hash-1"}))
        tracker = HashTracker(registry_path)
        assert tracker.get("skill-1") == "hash-1"
