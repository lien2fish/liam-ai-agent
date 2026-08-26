"""產生 The Unknown Hour 的懸疑背景音樂（純合成，不需任何素材）。

    python3 youtube_auto/make_bgm.py [輸出檔]     # 預設 youtube_auto/bgm.mp3

聲音設計＝D 小調低音 drone ＋ 三全音陰影 ＋ 心跳脈衝 ＋ 時鐘滴答（呼應頻道名的「時間」）。
所有頻率都量化成 1/LOOP_SEC 的整數倍、殘響用循環位移做，因此首尾接得起來——
build_video 是用 -stream_loop -1 無限循環播放，接縫會被聽出來。

要調整氛圍改下面的參數區就好。
"""

import os
import subprocess
import sys
import wave

import numpy as np

SR = 44100
LOOP_SEC = 60.0

ROOT = 36.71  # D1，整首的地基
DETUNE = 0.12  # 兩顆振盪器的頻差，做出緩慢的拍頻
TRITONE = 103.83  # G#2，不安感來源
PAD = (146.83, 174.61, 220.00)  # D3 / F3 / A3 小三和弦

HEARTBEAT_SEC = 2.0  # 心跳間隔
TICK_SEC = 1.0  # 滴答間隔

LEVEL = {
    "drone": 0.55,
    "tritone": 0.10,
    "pad": 0.09,
    "heartbeat": 0.30,
    "tick": 0.05,
    "shimmer": 0.020,
    "air": 0.035,
}
PEAK = 0.85

N = int(SR * LOOP_SEC)
T = np.arange(N) / SR


def q(freq):
    """把頻率吸附到 1/LOOP_SEC 的整數倍，確保整段首尾相位連續"""
    return max(1, round(freq * LOOP_SEC)) / LOOP_SEC


def sine(freq, phase=0.0):
    return np.sin(2 * np.pi * q(freq) * T + phase)


def lfo(period_sec, lo=0.0, hi=1.0):
    """0~1 的慢速起伏，週期需整除 LOOP_SEC 才不會在接縫跳掉"""
    return lo + (hi - lo) * (0.5 - 0.5 * np.cos(2 * np.pi * q(1 / period_sec) * T))


def loop_noise(seed, tilt=1.0):
    """頻域造噪音：隨機相位 + 1/f^tilt 傾斜，irfft 出來天生就是循環的"""
    rng = np.random.default_rng(seed)
    bins = N // 2 + 1
    freqs = np.arange(bins) / LOOP_SEC
    mag = np.zeros(bins)
    mag[1:] = 1.0 / np.power(freqs[1:], tilt)
    spec = mag * np.exp(1j * rng.uniform(0, 2 * np.pi, bins))
    out = np.fft.irfft(spec, N)
    return out / (np.max(np.abs(out)) or 1.0)


def stamp(dst, wave_, period_sec, amp=1.0, offset=0.0):
    """把一小段波形每隔 period_sec 蓋一次，超出結尾的尾巴繞回開頭

    offset 用來把敲擊點錯開 t=0——起音落在循環接縫上雖然仍是連續的，
    但驗接縫時很難跟爆音區分，錯開比較好檢查。
    """
    hit = wave_ * amp
    for k in range(int(round(LOOP_SEC / period_sec))):
        s = int(round((k * period_sec + offset) * SR))
        idx = (np.arange(len(hit)) + s) % N
        np.add.at(dst, idx, hit)


def heartbeat_hit():
    d = np.arange(int(0.45 * SR)) / SR
    body = np.sin(2 * np.pi * 58 * d) * np.exp(-d * 9.0)
    click = np.sin(2 * np.pi * 128 * d) * np.exp(-d * 40.0) * 0.25
    single = body + click
    second = np.zeros_like(single)
    off = int(0.30 * SR)
    second[off:] = single[: len(single) - off] * 0.62
    return single + second


def tick_hit():
    d = np.arange(int(0.02 * SR)) / SR
    rng = np.random.default_rng(7)
    n = rng.uniform(-1, 1, len(d))
    n = np.convolve(n, [1, -0.85], mode="same")  # 拉高頻，聽起來像秒針
    return n * np.exp(-d * 260.0)


def echo(sig, taps):
    """循環位移殘響：延遲用 np.roll，繞回開頭，所以不會破壞循環"""
    out = sig.copy()
    for delay_sec, gain in taps:
        out += np.roll(sig, int(delay_sec * SR)) * gain
    return out


def build():
    breath = lfo(20.0, 0.72, 1.0)  # 整體的呼吸感

    drone = (
        sine(ROOT)
        + sine(ROOT + DETUNE)
        + sine(ROOT * 2) * 0.55
        + sine(ROOT * 2 + DETUNE * 1.7) * 0.35
    ) * breath

    tritone = sine(TRITONE) * lfo(30.0, 0.0, 1.0)

    pad = np.zeros(N)
    for i, f in enumerate(PAD):
        pad += sine(f, phase=i * 1.1) * lfo(30.0 if i % 2 == 0 else 20.0, 0.05, 1.0)
    pad /= len(PAD)

    beat = np.zeros(N)
    stamp(beat, heartbeat_hit(), HEARTBEAT_SEC)

    tick = np.zeros(N)
    stamp(tick, tick_hit(), TICK_SEC, offset=0.5)

    shimmer = sine(1760.0) * lfo(7.5, 0.0, 1.0) * lfo(20.0, 0.2, 1.0)
    air = loop_noise(20260826, tilt=1.25) * lfo(30.0, 0.35, 1.0)

    mix = (
        drone * LEVEL["drone"]
        + tritone * LEVEL["tritone"]
        + pad * LEVEL["pad"]
        + beat * LEVEL["heartbeat"]
        + tick * LEVEL["tick"]
        + shimmer * LEVEL["shimmer"]
        + air * LEVEL["air"]
    )
    mix = echo(mix, [(0.31, 0.26), (0.53, 0.17), (0.89, 0.10)])
    mix = np.tanh(mix * 1.15)
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
    print(f"✅ {out}（{LOOP_SEC:.0f} 秒，可無縫循環）")


if __name__ == "__main__":
    main()
