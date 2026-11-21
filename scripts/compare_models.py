"""同じ音声を日本語モデルごとに認識させ、結果と処理時間を並べて表示する。

    python scripts/compare_models.py                 # マイクで10秒録音して比べる
    python scripts/compare_models.py --seconds 15    # 録音の長さを変える
    python scripts/compare_models.py rec.wav         # 録音済みの WAV（16kHz、モノラル）で比べる

録音は recordings/ に WAV で保存する。同じ録音で何度でも比べ直せる。
足りないモデルは models/ にダウンロードする（このスクリプトだけがネットワークを使う）。
認識はアプリと同じ方法（ストリーミングに音声を少しずつ渡す）で行う。
"""

from __future__ import annotations

import argparse
import sys
import time
import wave
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_model import fetch  # noqa: E402
from moonshine_dictate.engine import BLOCK_FRAMES, MODEL_DIRS, SAMPLE_RATE  # noqa: E402

COMPARE = ["small-streaming", "base", "tiny-streaming"]


def record(seconds: float, device: str) -> np.ndarray:
    import sounddevice as sd

    from moonshine_dictate.engine import find_input_device

    print(f"{seconds:.0f}秒間録音します。合図のあとに話してください。")
    for i in (3, 2, 1):
        print(f"  {i}…", flush=True)
        time.sleep(1)
    print("  話してください", flush=True)
    audio = sd.rec(int(seconds * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1,
                   dtype="float32", device=find_input_device(device))
    sd.wait()
    print("  録音を終えました\n")
    return audio[:, 0]


def save_wav(audio: np.ndarray) -> Path:
    out = ROOT / "recordings" / f"rec-{datetime.now():%Y%m%d-%H%M%S}.wav"
    out.parent.mkdir(exist_ok=True)
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())
    return out


def load_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2 or w.getframerate() != SAMPLE_RATE:
            raise SystemExit(f"{path} は 16kHz・モノラル・16bit の WAV にしてください")
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
    return pcm.astype(np.float32) / 32768


def report_level(audio: np.ndarray) -> None:
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    rms = float(np.sqrt(np.mean(audio ** 2))) if audio.size else 0.0
    db = 20 * np.log10(peak) if peak > 0 else -120
    print(f"録音の音量: 最大 {db:.0f} dBFS（RMS {rms:.4f}）")
    if db < -30:
        print("  ※ 音量がかなり小さいです。マイクの入力レベルを上げると精度が上がる可能性があります")
    if peak >= 0.99:
        print("  ※ 音が割れています。マイクの入力レベルを下げてください")
    print()


def transcribe(arch_key: str, audio: np.ndarray) -> tuple[str, float, float]:
    """アプリと同じく、ストリーミングに少しずつ音声を渡して認識する。(テキスト, 読み込み秒, 認識秒)"""
    from moonshine_voice import ModelArch, Transcriber

    path = fetch(arch_key, force=False)
    t0 = time.monotonic()
    transcriber = Transcriber(str(path), ModelArch[MODEL_DIRS[arch_key][1]])
    load_sec = time.monotonic() - t0
    lines: dict = {}
    stream = transcriber.create_stream()
    stream.add_listener(lambda e: getattr(e, "line", None) and lines.__setitem__(e.line.line_id, e.line.text))
    t0 = time.monotonic()
    stream.start()
    for i in range(0, len(audio), BLOCK_FRAMES):
        stream.add_audio(audio[i:i + BLOCK_FRAMES].tolist(), SAMPLE_RATE)
    stream.stop()
    run_sec = time.monotonic() - t0
    stream.close()
    transcriber.close()
    return "".join(t.strip() for t in lines.values() if t), load_sec, run_sec


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("wav", nargs="?", type=Path, help="録音済みの WAV。省略するとマイクで録音する")
    parser.add_argument("--seconds", type=float, default=10)
    parser.add_argument("--device", default="", help="マイクのデバイス名（一部でも可）")
    parser.add_argument("--models", default=",".join(COMPARE),
                        help=f"比べるモデル（カンマ区切り）。使える値: {', '.join(MODEL_DIRS)}")
    args = parser.parse_args()

    if args.wav:
        audio = load_wav(args.wav)
    else:
        audio = record(args.seconds, args.device)
        print(f"録音を保存しました: {save_wav(audio)}")
    report_level(audio)

    length = len(audio) / SAMPLE_RATE
    for arch_key in [m.strip() for m in args.models.split(",") if m.strip()]:
        print(f"[{arch_key}]", flush=True)
        try:
            text, load_sec, run_sec = transcribe(arch_key, audio)
        except Exception as e:
            print(f"  失敗しました: {e}\n")
            continue
        print(f"  {text or '（何も認識されませんでした）'}")
        print(f"  読み込み {load_sec:.1f}秒 / 認識 {run_sec:.1f}秒（音声 {length:.1f}秒）\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
