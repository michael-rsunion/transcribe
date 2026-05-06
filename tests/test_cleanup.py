import os
import time

from app.services.cleanup import drop_request_dir, make_request_dir, sweep_orphans


def test_make_and_drop(tmp_path):
    d = make_request_dir(tmp_path, "uuid1")
    assert d.exists() and d.is_dir() and d.parent == tmp_path
    (d / "v.mp4").write_bytes(b"x")
    drop_request_dir(d)
    assert not d.exists()


def test_drop_idempotent(tmp_path):
    drop_request_dir(tmp_path / "nope")  # no error


def test_sweep_orphans_removes_old(tmp_path):
    old = tmp_path / "old"
    old.mkdir()
    (old / "x").write_bytes(b"x")
    new = tmp_path / "new"
    new.mkdir()
    two_hours_ago = time.time() - 7200
    os.utime(old, (two_hours_ago, two_hours_ago))
    removed = sweep_orphans(tmp_path, max_age_seconds=3600)
    assert removed == 1
    assert not old.exists()
    assert new.exists()


def test_sweep_orphans_empty_base(tmp_path):
    nonexistent = tmp_path / "nope"
    assert sweep_orphans(nonexistent) == 0
