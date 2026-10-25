"""Unit tests for logic that is easy to break silently. Run: cd automation && python -m pytest -q"""
import json

import pytest

from ytauto import captions
from ytauto.assets import fetch
from ytauto.research import youtube_public as yp
from ytauto.voice import tts


# --------------------------------------------------------------- YouTube page parsing
@pytest.mark.parametrize("s,expected", [
    ("29,581,142 views", 29581142), ("4.9M", 4900000), ("1.2K views", 1200), ("No views", 0),
    ("25.8M subscribers", 25800000), (None, None)])
def test_parse_count(s, expected):
    assert yp.parse_count(s) == expected


@pytest.mark.parametrize("s,days", [("10y ago", 3652.5), ("3 weeks ago", 21), ("5d ago", 5), ("1 month ago", 30.44),
                                    ("Streamed 2 days ago", 2)])
def test_parse_age(s, days):
    assert yp.parse_age_days(s) == pytest.approx(days, rel=0.01)


def test_parse_duration():
    assert yp.parse_duration("1:02:03") == 3723 and yp.parse_duration("5:56") == 356


# --------------------------------------------------------------- licence gate
def _meta(desc="", secondary=""):
    return {"AVAIL:Description": desc, "AVAIL:SecondaryCreator": secondary}


def test_licence_blocks_noncommercial_in_secondary_field():
    with pytest.raises(fetch.AssetError):
        fetch.nasa_license_check("X", _meta(secondary="Image processing by Someone CC BY-NC-SA 3.0"))


def test_licence_blocks_citizen_without_open_licence():
    with pytest.raises(fetch.AssetError):
        fetch.nasa_license_check("X", _meta("Enhanced image by Jason Major based on images provided courtesy of NASA"))


def test_licence_allows_cc_by_citizen_and_credits_name():
    r = fetch.nasa_license_check("X", _meta(
        "Enhanced image by Kevin M. Gill (CC-BY) based on images provided courtesy of NASA/JPL-Caltech/SwRI/MSSS."))
    assert "Kevin M. Gill" in r["credit"] and r["flags"]


def test_licence_allows_plain_nasa():
    r = fetch.nasa_license_check("X", _meta("Juno acquired this image.", "NASA/JPL-Caltech/SwRI/MSSS"))
    assert r["credit"] == "NASA/JPL-Caltech/SwRI/MSSS" and not r["flags"]


def test_licence_override_is_explicit():
    r = fetch.nasa_license_check("X", _meta(secondary="CC BY-NC"), {"license_override": "written permission 2026-10-25"})
    assert "override" in r["flags"][0]


# --------------------------------------------------------------- text & captions
def test_sentence_split_keeps_abbreviations_and_decimals():
    s = tts.split_sentences("Water is about 0.25 percent. Dr. Smith agreed. Done!")
    assert s == ["Water is about 0.25 percent.", "Dr. Smith agreed.", "Done!"]


def test_lexicon_whole_words_only():
    assert tts.pronounce("Io and Iota", {"Io": "Eye-oh"}) == "Eye-oh and Iota"


def test_captions_line_limits_and_coverage():
    timings = {"scenes": [{"sentences": [{"text": "word " * 40, "start": 1.0, "end": 11.0}]}]}
    cs = captions.cues(timings)
    assert all(len(l) <= captions.MAX_LINE for _, _, t in cs for l in t.split("\n"))
    assert cs[0][0] == 1.0 and cs[-1][1] == pytest.approx(11.0)


# --------------------------------------------------------------- timeline
class _Spec:
    def __init__(self, scenes):
        self.scenes = scenes


def test_timeline_is_contiguous_and_snaps_to_sentence_gaps():
    from ytauto.video import timeline
    sc = [{"id": "a", "beats": [{"type": "fact", "sentences": 1}, {"type": "fact", "sentences": 1}]}]
    tm = {"duration": 12.0, "scenes": [{"start": 0.4, "end": 10.0, "sentences": [
        {"start": 0.4, "end": 4.8}, {"start": 5.2, "end": 10.0}]}]}
    beats = timeline.build(_Spec(sc), tm)
    assert beats[0]["start"] == 0 and beats[-1]["end"] == 12.0
    assert beats[0]["end"] == beats[1]["start"] == pytest.approx(5.0)


# --------------------------------------------------------------- publish safety gate
def test_publish_gate_blocks_public_without_authorisation(tmp_path, monkeypatch):
    from ytauto.publish import youtube

    class S:
        out = tmp_path
    (tmp_path / "qa.json").write_text(json.dumps({"summary": {"FAIL": 0}}))
    for name in ("v.mp4", "t.jpg", "c.srt"):
        (tmp_path / name).write_text("x")
    req = {"body": {"status": {"privacyStatus": "public"}},
           "files": {"video": str(tmp_path / "v.mp4"), "thumbnail": str(tmp_path / "t.jpg"),
                     "captions": str(tmp_path / "c.srt")}}
    monkeypatch.delenv("YTAUTO_ALLOW_PUBLIC", raising=False)
    with pytest.raises(youtube.PublishBlocked):
        youtube._gate(S, req)
    req["body"]["status"]["privacyStatus"] = "private"
    youtube._gate(S, req)  # private passes


def test_publish_gate_blocks_on_qa_fail(tmp_path):
    from ytauto.publish import youtube

    class S:
        out = tmp_path
    (tmp_path / "qa.json").write_text(json.dumps({"summary": {"FAIL": 2}}))
    with pytest.raises(youtube.PublishBlocked):
        youtube._gate(S, {"body": {"status": {"privacyStatus": "private"}}, "files": {}})
