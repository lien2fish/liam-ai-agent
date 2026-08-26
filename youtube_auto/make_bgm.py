"""產生 The Unknown Hour 的背景音樂（純合成，不需任何素材）。

    python3 youtube_auto/make_bgm.py [輸出檔]     # 預設 youtube_auto/bgm.mp3

慢速流行編制：D 小調四和弦進行 ＋ 貝斯 ＋ 鐘琴主旋律 ＋ 鼓組（kick／clap／shaker）。
BPM 75、16 小節一輪，整首 51.2 秒可無縫循環——build_video 是 -stream_loop -1 無限
循環播放，接縫會被聽出來，所以殘響用循環位移、所有事件的尾巴都繞回開頭。

主旋律刻意放在 1000Hz 以上的鐘琴音域：旁白佔 100-3000Hz，旋律壓在同一區會糊掉人聲。

要調整改下面的參數區：BPM、PROG（和弦進行）、MELODY（主旋律）、LEVEL（各層音量）。
"""

import os
import subprocess
import sys
import wave

import numpy as np

SR = 44100
BPM = 75
BEAT = 60.0 / BPM
BAR = 4 * BEAT
BARS = 16
LOOP_SEC = BARS * BAR

# 和弦進行：(和弦音, 佔幾小節)，D 小調 i-VI-III-VII，跑兩輪
PROG = [("Dm", 2), ("Bb", 2), ("F", 2), ("C", 2)] * 2

CHORDS = {
    "Dm": [("D", 3), ("F", 3), ("A", 3)],
    "Bb": [("Bb", 2), ("D", 3), ("F", 3)],
    "F": [("F", 2), ("A", 2), ("C", 3)],
    "C": [("C", 3), ("E", 3), ("G", 3)],
}
BASS = {"Dm": ("D", 1), "Bb": ("Bb", 1), "F": ("F", 1), "C": ("C", 2)}

# 主旋律：(第幾拍起, 幾拍長, 音名, 第幾八度)。八度 5-6＝鐘琴音域，讓開人聲
MELODY = [
    (0, 3, "A", 5),
    (3, 1, "D", 6),
    (4, 4, "F", 5),
    (8, 3, "D", 6),
    (11, 1, "C", 6),
    (12, 4, "A", 5),
    (16, 3, "F", 5),
    (19, 1, "G", 5),
    (20, 4, "A", 5),
    (24, 6, "D", 6),
    (32, 3, "A", 5),
    (35, 1, "D", 6),
    (36, 4, "F", 6),
    (40, 3, "E", 6),
    (43, 1, "D", 6),
    (44, 4, "C", 6),
    (48, 3, "D", 6),
    (51, 1, "A", 5),
    (52, 4, "F", 5),
    (56, 8, "D", 5),
]

LEVEL = {
    "pad": 0.30,
    "bass": 0.42,
    "melody": 0.26,
    "kick": 0.30,
    "clap": 0.10,
    "shaker": 0.045,
    "air": 0.025,
}
PEAK = 0.85

N = int(SR * LOOP_SEC)
T = np.arange(N) / SR
_SEMI = {
    "C": 0,
    "C#": 1,
    "D": 2,
    "D#": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "G": 7,
    "G#": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
}


def hz(name, octave):
    return 440.0 * 2 ** ((_SEMI[name] - 9 + (octave - 4) * 12) / 12.0)


def place(dst, wave_, start_sec, amp=1.0):
    """把一段波形放到指定時間，超出結尾的部分繞回開頭，維持循環"""
    hit = wave_ * amp
    s = int(round(start_sec * SR))
    idx = (np.arange(len(hit)) + s) % N
    np.add.at(dst, idx, hit)


def _env(n, attack, decay, sustain, release):
    """ADSR，長度 n 個樣本"""
    a, d, r = int(attack * SR), int(decay * SR), int(release * SR)
    a, d = min(a, n), min(d, max(0, n - a))
    s = max(0, n - a - d - r)
    r = max(0, n - a - d - s)
    return np.concatenate(
        [
            np.linspace(0, 1, a, endpoint=False),
            np.linspace(1, sustain, d, endpoint=False),
            np.full(s, sustain),
            np.linspace(sustain, 0, r),
        ]
    )[:n]


def tone(freq, dur, harmonics, attack, decay, sustain, release, vibrato=0.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = freq * (1 + vibrato * np.sin(2 * np.pi * 5.0 * t)) if vibrato else freq
    out = np.zeros(n)
    for k, amp in harmonics:
        out += amp * np.sin(2 * np.pi * f * k * t)
    return out * _env(n, attack, decay, sustain, release)


def pad_voice(freq, dur):
    """墊音：兩顆微失諧振盪器，慢起慢收"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = (
        np.sin(2 * np.pi * freq * t)
        + 0.7 * np.sin(2 * np.pi * (freq * 1.003) * t)
        + 0.35 * np.sin(2 * np.pi * freq * 2 * t)
    )
    return sig * _env(n, 0.55, 0.5, 0.72, 0.9)


def kick():
    n = int(0.42 * SR)
    t = np.arange(n) / SR
    f = 105 * np.exp(-t * 22) + 42  # 頻率下滑＝流行鼓組的 kick
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 7.5)


def clap(seed=3):
    n = int(0.28 * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    body = rng.uniform(-1, 1, n)
    body = np.convolve(body, np.hanning(24), mode="same")
    env = np.exp(-t * 16)
    for off in (0.010, 0.021):  # 三下極短的前擊，聽起來才像拍手不像雜訊
        k = int(off * SR)
        env[k:] += np.exp(-t[: n - k] * 26) * 0.6
    return body * env


def shaker(seed):
    n = int(0.07 * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    s = rng.uniform(-1, 1, n)
    s = np.convolve(s, [1, -0.9], mode="same")  # 拉高頻
    return s * np.exp(-t * 55)


def loop_noise(seed, tilt=1.2):
    """頻域造噪音：irfft 出來天生就是循環的"""
    rng = np.random.default_rng(seed)
    bins = N // 2 + 1
    freqs = np.arange(bins) / LOOP_SEC
    mag = np.zeros(bins)
    mag[1:] = 1.0 / np.power(freqs[1:], tilt)
    out = np.fft.irfft(mag * np.exp(1j * rng.uniform(0, 2 * np.pi, bins)), N)
    return out / (np.max(np.abs(out)) or 1.0)


def echo(sig, taps):
    out = sig.copy()
    for delay_sec, gain in taps:
        out += np.roll(sig, int(delay_sec * SR)) * gain
    return out


def build():
    pad = np.zeros(N)
    bass = np.zeros(N)
    mel = np.zeros(N)


    bar = 0
    for name, span in PROG:
        t0 = bar * BAR
        dur = span * BAR
        for note, octv in CHORDS[name]:
            place(pad, pad_voice(hz(note, octv), dur), t0)
        bn, bo = BASS[name]
        for b in range(span * 4):  # 每拍一顆貝斯，第一拍重
            amp = 1.0 if b % 4 == 0 else 0.55
            place(
                bass,
                tone(
                    hz(bn, bo),
                    BEAT * 0.9,
                    [(1, 1.0), (2, 0.25)],
                    0.008,
                    0.10,
                    0.55,
                    0.18,
                ),
                t0 + b * BEAT,
                amp,
            )
        bar += span

    for beat_i, beats, note, octv in MELODY:
        place(
            mel,
            tone(
                hz(note, octv),
                beats * BEAT * 0.95,
                [(1, 1.0), (2, 0.30), (3, 0.12)],
                0.02,
                0.35,
                0.45,
                0.45,
                vibrato=0.0016,
            ),
            beat_i * BEAT,
        )

    kicks, claps, shakers = np.zeros(N), np.zeros(N), np.zeros(N)
    k, c = kick(), clap()
    for b in range(BARS * 4):
        t0 = b * BEAT
        if b % 4 in (0, 2):
            place(kicks, k, t0)
        if b % 4 in (1, 3):
            place(claps, c, t0)
        for half in (0, 0.5):  # 八分音符 shaker，反拍輕一點
            place(
                shakers,
                shaker(b * 2 + int(half * 2)),
                t0 + half * BEAT,
                0.6 if half else 1.0,
            )

    mix = (
        pad * LEVEL["pad"]
        + bass * LEVEL["bass"]
        + mel * LEVEL["melody"]
        + kicks * LEVEL["kick"]
        + claps * LEVEL["clap"]
        + shakers * LEVEL["shaker"]
        + loop_noise(20260826) * LEVEL["air"]
    )
    mix = echo(mix, [(BEAT * 0.75, 0.17), (BEAT * 1.5, 0.09)])
    mix = np.tanh(mix * 1.1)
    return mix / (np.max(np.abs(mix)) or 1.0) * PEAK


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(sys.path[0], "bgm.mp3")
    audio = build()
    tmp = out + ".tmp.wav"
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((audio * 32767).astype("<i2").tobytes())
    subprocess.run(
        ["ffmpeg", "-y", "-i", tmp, "-c:a", "libmp3lame", "-b:a", "192k", out],
        check=True,
        capture_output=True,
    )
    os.remove(tmp)
    print(f"✅ {out}（BPM {BPM}、{BARS} 小節、{LOOP_SEC:.1f} 秒，可無縫循環）")


if __name__ == "__main__":
    main()
