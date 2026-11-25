"""剪掉空檔後，把舊長片的時間點換算到新長片（資訊卡、子母畫面、章節）。

    /usr/bin/python3 remap_long.py 舊_段落時間.json 新_段落時間.json 秒數 ...

素材時間落在被剪掉的空檔裡，就對到下一段保留畫面的開頭。
"""

import sys, json

SPEED = 1.2
old, new = (json.load(open(p)) for p in sys.argv[1:3])


def remap(t):
    for i, (o, f, a, b) in enumerate(old):
        nxt = old[i + 1][0] if i + 1 < len(old) else 1e9
        if o <= t < nxt:
            s = a + (t - o) * SPEED
            break
    later = [(no, na, nb) for no, nf, na, nb in new if nf == f and nb > s]
    no, na, nb = min(later, key=lambda x: x[1])
    return round(no + max(0, s - na) / SPEED, 2)


if __name__ == "__main__":
    for t in sys.argv[3:]:
        print(t, remap(float(t)))
