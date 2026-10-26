"""Tests for the cinematic layer: HUD value formatting, render cache keys, music cue sheet, SFX timing."""
import numpy as np
import pytest

from ytauto.audio import music, sfx
from ytauto.video import prerender
from ytauto.visuals import editorial as ed
from ytauto.visuals import shots


@pytest.mark.parametrize("key,spec,u,expected", [
    ("speed", [170590, 170590, "km/h"], 0.5, "170,590 km/h"),
    ("pressure", [0.1, 1.0, "bar"], 0.0, "0.1 bar"),
    ("pressure", [0.1, 1.0, "bar"], 1.0, "1.0 bar"),
    ("temp", [-161, -108, "°C"], 1.0, "-108 °C"),
    ("g", [12, 228, "g"], 1.0, "228 g"),
    ("clock", ["22:04:30", "22:04:44"], 1.0, "22:04:44"),
    ("clock", ["22:05", "23:02"], 1.0, "23:02"),
    ("clock", ["T+57:30", "T+58:00"], 1.0, "T+58:00"),
    ("date", "07 DEC 1995", 0.3, "07 DEC 1995"),
])
def test_hud_values(key, spec, u, expected):
    assert ed.hud_value(key, spec, u) == expected


def test_hud_log_interpolation_for_huge_ranges():
    mid = ed.hud_value("distance", [80, 80000, "km"], 0.5)
    assert mid == "2,530 km"   # geometric midpoint, not 40,040


def test_clip_key_depends_on_params_and_duration():
    b = {"type": "r3d", "shot": "orbit", "params": {"dist": [3, 2]}}
    k1 = prerender.clip_key(b, 5.0)
    assert k1 == prerender.clip_key(dict(b), 5.0)
    assert k1 != prerender.clip_key(b, 6.0)
    assert k1 != prerender.clip_key({**b, "params": {"dist": [3, 2.5]}}, 5.0)


def test_lightning_times_are_deterministic_and_inside_shot():
    a = shots.lightning_times(10.0, lightning=2.0, seed=21)
    assert a == shots.lightning_times(10.0, lightning=2.0, seed=21)
    assert a and all(0 < t < 10.0 for t in a)
    assert shots.lightning_times(10.0, lightning=0.0) == []


def test_music_credit_requires_known_licence():
    assert "CC BY 4.0" in music.track_credit("zero-project-the-passage")
    with pytest.raises(ValueError):
        music.track_credit("some-random-track")


def test_cue_bed_silence_is_silent(monkeypatch):
    sr = 8000
    monkeypatch.setattr(music, "_load_track", lambda tid, s: np.full((sr * 30, 2), 0.1, np.float32))
    cues = [{"scene": "a", "track": "zero-project-x", "offset": 0, "gain_db": -20},
            {"scene": "b", "track": "silence"},
            {"scene": "c", "track": "zero-project-y", "offset": 0, "gain_db": -20}]
    bed, placed = music.cue_bed(cues, {"a": 0.0, "b": 10.0, "c": 20.0}, 30.0, sr)
    assert np.abs(bed[int(10.5 * sr):int(19.9 * sr)]).max() == 0
    assert np.abs(bed[int(2 * sr):int(9 * sr)]).max() > 0
    assert [p["start"] for p in placed] == [0.0, 10.0, 20.0]


def test_sfx_design_places_thunder_after_flash():
    beats = [{"type": "r3d", "shot": "cloud_dive", "params": {"lightning": 2.0, "seed": 21, "decks": 1},
              "start": 5.0, "end": 15.0}]
    out = sfx.design(beats, 20.0)
    assert out.shape == (20 * sfx.SR, 2)
    assert np.abs(out[: 4 * sfx.SR]).max() < 1e-6          # nothing before the shot starts
    assert np.abs(out[5 * sfx.SR:15 * sfx.SR]).max() > 0.05
