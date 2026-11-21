"""同梱する日本語モデルを models/ にダウンロードする（ビルド前に1回実行する）。

    python scripts/fetch_model.py                # small-streaming-ja（同梱する標準のモデル）
    python scripts/fetch_model.py tiny-streaming # tiny-streaming-ja
    python scripts/fetch_model.py base           # base-ja（ストリーミング非対応）

アプリ本体はネットワーク通信をしない（要件 R2.3）。ダウンロードはこのスクリプトだけが行う。
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from moonshine_dictate.engine import MODEL_DIRS  # noqa: E402


def fetch(arch_key: str, force: bool = True) -> Path:
    """モデルを models/ に保存し、その場所を返す。force=False なら、すでにあれば何もしない。"""
    from moonshine_voice import ModelArch
    from moonshine_voice.download import get_model_for_language

    dirname, arch_name = MODEL_DIRS[arch_key]
    dest = ROOT / "models" / dirname
    if dest.is_dir() and not force:
        return dest
    with tempfile.TemporaryDirectory() as tmp:
        path, _ = get_model_for_language("ja", ModelArch[arch_name], cache_root=Path(tmp))
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(path, dest)
    return dest


def main(argv: list[str]) -> int:
    # Windows のコンソール（cp1252 など）でも日本語のメッセージで落ちないようにする
    sys.stdout.reconfigure(errors="replace")
    arch_key = argv[0] if argv else "small-streaming"
    if arch_key not in MODEL_DIRS:
        print(f"モデルの種類は {', '.join(MODEL_DIRS)} のどれかを指定してください")
        return 2
    dest = fetch(arch_key)
    total = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file())
    print(f"{dest} に保存しました（{total / 1e6:.1f}MB）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
