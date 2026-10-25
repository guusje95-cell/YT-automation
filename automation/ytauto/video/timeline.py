"""Turn scenes + narration timings into a flat list of timed beats.

Each beat may carry `sentences: n` (a weight). Weights are mapped onto the scene's
time span proportionally and every cut is snapped to the nearest sentence
boundary (within 1.2 s) so visuals change on natural pauses.
"""
from __future__ import annotations


def build(spec, timings: dict) -> list[dict]:
    beats_out = []
    scenes = timings["scenes"]
    for i, (sc, tm) in enumerate(zip(spec.scenes, scenes)):
        start = 0.0 if i == 0 else tm["start"]
        end = scenes[i + 1]["start"] if i + 1 < len(scenes) else timings["duration"]
        bounds = [s["end"] for s in tm["sentences"][:-1]]
        # midpoint of the gap after each sentence is the natural cut point
        cuts_nat = [(b + nxt["start"]) / 2 for b, nxt in zip(bounds, tm["sentences"][1:])]
        beats = sc["beats"]
        weights = [max(float(b.get("sentences", 1)), 0.25) for b in beats]
        total = sum(weights)
        span = end - start
        acc, edges = 0.0, [start]
        for w in weights[:-1]:
            acc += w
            target = start + span * acc / total
            near = min(cuts_nat, key=lambda c: abs(c - target)) if cuts_nat else None
            edge = near if near is not None and abs(near - target) < 1.2 and near > edges[-1] + 1.5 else target
            edges.append(edge)
        edges.append(end)
        for k, b in enumerate(beats):
            beats_out.append({**b, "scene": sc["id"], "chapter": sc.get("chapter"), "scene_index": i,
                              "first_in_scene": k == 0, "start": round(edges[k], 3),
                              "end": round(edges[k + 1], 3)})
    # guarantee monotonic, minimum 1.2 s beats
    for b in beats_out:
        if b["end"] - b["start"] < 1.2:
            b["end"] = b["start"] + 1.2
    for a, b in zip(beats_out, beats_out[1:]):
        b["start"] = a["end"]
        if b["end"] <= b["start"]:
            b["end"] = b["start"] + 1.2
    return beats_out
