#!/usr/bin/env python3
"""Verify an audio file exported by the Ardour headless tests.

Usage: check-export.py <file.wav> <expected-seconds> [min-rms-dbfs [max-peak]]

Parses the RIFF/WAVE (or RF64) container directly so that 16/24/32-bit
PCM and 32-bit float exports are all handled, then checks the duration
and that the signal is neither silent nor clipped garbage.
"""
import math
import struct
import sys


def read_wav(path):
    with open(path, "rb") as f:
        data = f.read()
    riff, _, wave = struct.unpack_from("<4sI4s", data, 0)
    if riff not in (b"RIFF", b"RF64") or wave != b"WAVE":
        raise SystemExit(f"{path}: not a RIFF/RF64 WAVE file")
    pos = 12
    fmt = None
    pcm = None
    ds64_size = None
    while pos + 8 <= len(data):
        cid, size = struct.unpack_from("<4sI", data, pos)
        body = pos + 8
        if cid == b"ds64":
            ds64_size = struct.unpack_from("<Q", data, body + 8)[0]
        elif cid == b"fmt ":
            fmt = struct.unpack_from("<HHIIHH", data, body)
            if fmt[0] == 0xFFFE:  # WAVE_FORMAT_EXTENSIBLE
                sub = struct.unpack_from("<H", data, body + 24)[0]
                fmt = (sub,) + fmt[1:]
        elif cid == b"data":
            if size == 0xFFFFFFFF and ds64_size is not None:
                size = ds64_size
            pcm = data[body:body + size]
            break
        pos = body + size + (size & 1)
    if fmt is None or pcm is None:
        raise SystemExit(f"{path}: missing fmt or data chunk")
    tag, channels, rate, _, align, bits = fmt
    n = len(pcm) // align
    samples = []
    width = bits // 8
    for i in range(0, n * align, width):
        chunk = pcm[i:i + width]
        if tag == 3 and bits == 32:
            v = struct.unpack("<f", chunk)[0]
        elif tag == 1 and bits == 16:
            v = struct.unpack("<h", chunk)[0] / 32768.0
        elif tag == 1 and bits == 24:
            v = int.from_bytes(chunk, "little", signed=True) / 8388608.0
        elif tag == 1 and bits == 32:
            v = struct.unpack("<i", chunk)[0] / 2147483648.0
        else:
            raise SystemExit(f"{path}: unsupported format tag {tag}/{bits} bit")
        samples.append(v)
    return channels, rate, bits, n, samples


def main():
    path = sys.argv[1]
    expect = float(sys.argv[2])
    min_db = float(sys.argv[3]) if len(sys.argv) > 3 else -40.0
    max_peak = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0001
    channels, rate, bits, frames, samples = read_wav(path)
    secs = frames / rate
    rms = math.sqrt(sum(v * v for v in samples) / max(1, len(samples)))
    peak = max((abs(v) for v in samples), default=0.0)
    rms_db = 20 * math.log10(rms) if rms > 0 else -math.inf
    print(f"{path}: {channels} ch, {rate} Hz, {bits} bit, {frames} frames "
          f"({secs:.3f} s), rms {rms_db:.1f} dBFS, peak {peak:.3f}")
    ok = True
    if abs(secs - expect) > 0.05:
        print(f"FAIL: duration {secs:.3f} s, expected {expect} s")
        ok = False
    if rms_db < min_db:
        print(f"FAIL: signal too quiet ({rms_db:.1f} dBFS < {min_db} dBFS)")
        ok = False
    if peak > max_peak:
        print(f"FAIL: peak {peak:.4f} exceeds {max_peak}")
        ok = False
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
