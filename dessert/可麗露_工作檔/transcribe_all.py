"""可麗露素材批次轉錄。輸出格式同 reel_maker transcribe()，但關掉 condition_on_previous_text（避免幻覺傳染）。"""
import sys, os, json, glob, warnings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../tools"))
import numpy as np, wave, whisper
from reel_maker import extract_audio

warnings.filterwarnings("ignore")
SRC = os.path.join(os.path.dirname(__file__), "../../素材/可麗露")
OUT = os.path.join(os.path.dirname(__file__), "transcripts")
m = whisper.load_model(sys.argv[1] if len(sys.argv) > 1 else "medium")
for v in sorted(glob.glob(os.path.join(SRC, "*.MOV"))):
    name = os.path.splitext(os.path.basename(v))[0]
    dst = os.path.join(OUT, name + ".json")
    if os.path.exists(dst):
        continue
    print("轉錄", name, flush=True)
    wav = extract_audio(v)
    r = m.transcribe(wav, language="zh", fp16=False, word_timestamps=True,
                     condition_on_previous_text=False,
                     initial_prompt="以下是甜點師製作可麗露的口語對話，繁體中文。")
    w = wave.open(wav, "rb"); sr = w.getframerate()
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    def db(s, e):
        seg = a[int(s * sr):int(e * sr)]
        return float(20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)) if len(seg) else -99.0
    segs = [{"start": round(float(s["start"]), 2), "end": round(float(s["end"]), 2),
             "text": s["text"].strip(), "db": round(db(s["start"], s["end"]), 1),
             "words": [{"w": x["word"].strip(), "s": round(x["start"], 2), "e": round(x["end"], 2)}
                       for x in s.get("words", []) if x["word"].strip()]} for s in r["segments"]]
    if segs:
        mx = max(x["db"] for x in segs)
        for x in segs:
            x["fg"] = bool(x["db"] >= mx - 8)
    json.dump(segs, open(dst, "w"), ensure_ascii=False, indent=1)
    os.remove(wav)
print("完成", flush=True)
