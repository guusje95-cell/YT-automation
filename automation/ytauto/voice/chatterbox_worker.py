"""Chatterbox TTS worker. Runs inside its own virtualenv (torch pinned by chatterbox-tts).

Protocol: one JSON object per stdin line {"text", "out", "exaggeration", "cfg_weight", "temperature", "seed"};
writes one JSON line per request to stdout: {"ok": true, "out": path, "sr": 24000} or {"ok": false, "error": ...}.
Started by ytauto.voice.tts.ChatterboxTTS; never run by hand except for debugging.
"""
import json
import os
import sys
import warnings

os.environ.setdefault("TQDM_DISABLE", "1")
warnings.filterwarnings("ignore")


def main():
    import torch
    import torchaudio as ta
    from chatterbox.tts import ChatterboxTTS
    torch.set_num_threads(int(os.environ.get("CBX_THREADS", "4")))
    ref = os.environ.get("CBX_REF") or None
    model = ChatterboxTTS.from_pretrained("cpu")
    if ref:
        model.prepare_conditionals(ref, exaggeration=float(os.environ.get("CBX_EXAG", "0.5")))
    conds = {ref: model.conds} if ref else {}
    current = ref
    print(json.dumps({"ready": True, "sr": model.sr}), flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        try:
            want = req.get("ref") or ref
            if want and want != current:  # switch speaker: cache conditionals per reference clip
                if want not in conds:
                    model.prepare_conditionals(want, exaggeration=float(req.get("exaggeration", 0.5)))
                    conds[want] = model.conds
                model.conds = conds[want]
                current = want
            if "seed" in req:
                torch.manual_seed(int(req["seed"]))
            wav = model.generate(req["text"], exaggeration=float(req.get("exaggeration", 0.5)),
                                 cfg_weight=float(req.get("cfg_weight", 0.4)),
                                 temperature=float(req.get("temperature", 0.8)))
            ta.save(req["out"], wav, model.sr)
            print(json.dumps({"ok": True, "out": req["out"], "sr": model.sr}), flush=True)
        except Exception as e:  # report and keep serving
            print(json.dumps({"ok": False, "error": repr(e)}), flush=True)


if __name__ == "__main__":
    main()
