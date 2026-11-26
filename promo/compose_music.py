"""Synthesize an original 30-second soundtrack for the promo (no samples, no licensing).

120 BPM, one chord per bar (2 s). Cuts at 4 s, 14 s and 26 s land on bar lines.
    .venv-run/Scripts/python.exe promo/compose_music.py  ->  promo/stylematch_music.wav
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR, DUR, BPM = 44100, 30.0, 120
BEAT = 60 / BPM
BAR = 4 * BEAT
N = int(SR * DUR)
t_all = np.arange(N) / SR
OUT = Path(__file__).resolve().parent / "stylematch_music.wav"


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


# Dmaj9 - Bm9 - Gmaj7(#11 colour) - A6sus, repeating; ends on Dmaj9.
CHORDS = [
    [50, 57, 61, 64, 66],   # D  A  C# E  F#
    [47, 54, 57, 61, 62],   # B  F# A  C# D
    [43, 50, 54, 59, 61],   # G  D  F# B  C#
    [45, 52, 54, 57, 59],   # A  E  F# A  B
]
BASS = [38, 35, 31, 33]
ARP = [[74, 78, 81, 76], [73, 74, 78, 81], [74, 78, 79, 83], [76, 78, 81, 83]]


def env(n, attack, release):
    e = np.ones(n)
    a, r = int(attack * SR), int(release * SR)
    if a:
        e[:a] = np.linspace(0, 1, a)
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def add(buf, start, signal, pan=0.0):
    i = int(start * SR)
    if i >= N:
        return
    signal = signal[: N - i]
    buf[0, i:i + len(signal)] += signal * np.sqrt((1 - pan) / 2)
    buf[1, i:i + len(signal)] += signal * np.sqrt((1 + pan) / 2)


def pad(freq, length):
    t = np.arange(int(length * SR)) / SR
    tone = sum(np.sin(2 * np.pi * freq * d * t + p) for d, p in ((1, 0), (1.003, 1.1), (0.997, 2.3)))
    tone += 0.25 * np.sin(2 * np.pi * freq * 2 * t)
    return tone / 3.3 * env(len(t), 0.6, 0.9)


def bell(freq, length=1.6, level=1.0):
    t = np.arange(int(length * SR)) / SR
    decay = np.exp(-t * 3.2)
    tone = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 2.01 * t) * np.exp(-t * 6)
    return level * tone * decay * env(len(t), 0.004, 0.05)


def bass(freq, length):
    t = np.arange(int(length * SR)) / SR
    tone = np.sin(2 * np.pi * freq * t) + 0.2 * np.sin(2 * np.pi * freq * 2 * t)
    return tone * np.exp(-t * 1.1) * env(len(t), 0.01, 0.2)


def kick():
    t = np.arange(int(0.35 * SR)) / SR
    sweep = 2 * np.pi * np.cumsum(48 + 90 * np.exp(-t * 32)) / SR
    return np.sin(sweep) * np.exp(-t * 9)


def hat(rng):
    t = np.arange(int(0.06 * SR)) / SR
    noise = np.diff(rng.standard_normal(len(t) + 1))  # crude high-pass
    return noise * np.exp(-t * 70) * 0.5


def reverb(buf, mix=0.28):
    wet = np.zeros_like(buf)
    for delay, gain in ((0.0297, 0.62), (0.0371, 0.58), (0.0411, 0.55), (0.0437, 0.52)):
        d = int(delay * SR)
        for ch in range(2):
            y = buf[ch].copy()
            for k in range(1, 12):
                shift = d * k + ch * 37
                if shift >= N:
                    break
                y[shift:] += buf[ch, :-shift] * gain ** k
            wet[ch] += y
    wet /= 4
    return buf * (1 - mix) + wet * mix


def main():
    rng = np.random.default_rng(7)
    music = np.zeros((2, N))
    bars = int(DUR / BAR)  # 15 bars
    for b in range(bars):
        start = b * BAR
        idx = 0 if b == bars - 2 or b == bars - 1 else b % 4
        length = BAR * (2 if b == bars - 2 else 1) + 0.9
        if b == bars - 1:
            continue  # the penultimate bar rings through the end
        for k, note in enumerate(CHORDS[idx]):
            add(music, start, 0.07 * pad(hz(note), length), pan=(k - 2) * 0.25)

        # bells: sparse in the intro, eighth-note arpeggio in the body, sparse again at the end
        body = 2 <= b < 13
        steps = 8 if body else 2
        for s in range(steps):
            note = ARP[idx][s % 4] + (12 if (s // 4) % 2 and body else 0)
            lvl = 0.10 if body else 0.14
            add(music, start + s * BAR / steps, bell(hz(note), level=lvl), pan=0.35 if s % 2 else -0.35)

        if 2 <= b < 13:
            add(music, start, 0.22 * bass(hz(BASS[idx]), BAR))
            add(music, start + 2.5 * BEAT, 0.12 * bass(hz(BASS[idx] + 7), BEAT * 1.5))
        if 4 <= b < 13:  # light pulse from 8 s
            for beat in range(4):
                add(music, start + beat * BEAT, 0.30 * kick() * (1 if beat % 2 == 0 else 0.55))
                add(music, start + beat * BEAT + BEAT / 2, 0.05 * hat(rng), pan=0.3)

    # accent chime when the 95 score lands (frame 566 = 18.87 s) and on the end card (26 s)
    for when, notes in ((18.87, (86, 90, 93)), (26.0, (74, 81, 86, 90))):
        for k, note in enumerate(notes):
            add(music, when + k * 0.06, bell(hz(note), 2.5, 0.09), pan=(k - 1) * 0.3)

    music = reverb(music)
    music *= env(N, 0.8, 2.2)
    music = np.tanh(music * 1.4) / np.tanh(1.4)
    music *= 0.85 / np.max(np.abs(music))
    pcm = (music.T * 32767).astype("<i2")
    with wave.open(str(OUT), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"wrote {OUT.name} ({DUR:.0f}s)")


if __name__ == "__main__":
    main()
