"""設定ファイル（TOML）の読み込みと検証（要件 R6）。

誤った項目は標準値に戻して動かし、誤りの内容を `Config.errors` に入れて返す（要件 R6.4）。
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from moonshine_dictate.platform_info import IS_MACOS

INSERT_METHODS = ("clipboard", "live")
LOG_LEVELS = ("error", "info", "debug")
MODEL_ARCHS = ("small-streaming", "tiny-streaming", "base")


def default_hotkey() -> str:
    return "ctrl+option+space" if IS_MACOS else "ctrl+alt+space"


@dataclass
class Config:
    hotkey: str = field(default_factory=default_hotkey)
    silence_timeout_sec: int = 60
    insert_method: str = "clipboard"
    restore_clipboard: bool = True
    input_device: str = ""
    sound: bool = True
    autostart: bool = False
    log_level: str = "info"
    model_dir: str = ""
    model_arch: str = "small-streaming"
    replace: dict[str, str] = field(default_factory=dict)
    # 読み込み時に見つかった誤り。設定項目ではない
    errors: list[str] = field(default_factory=list, compare=False)


TEMPLATE = """\
# moonshine-dictate の設定ファイル
# 変更したら、タスクトレイのメニューから「設定の再読み込み」を選ぶと反映されます。
# 項目を消すと標準値で動きます。

# 録音の開始・終了に使うキー。修飾キーは ctrl / alt（option）/ shift / cmd（win）
# 例: "ctrl+alt+space"、"ctrl+shift+d"、"f9"
hotkey = "{hotkey}"

# 無音がこの秒数続いたら録音を終了します
silence_timeout_sec = 60

# テキストの入れ方
#   "clipboard" : 録音の終了時に、全文をクリップボード経由で貼り付けます
#   "live"      : 話の区切りが確定するたびに、キー入力として送ります
insert_method = "clipboard"

# clipboard のとき、貼り付けた後に元のクリップボードの内容に戻すか
restore_clipboard = true

# マイクのデバイス名（一部だけでも可）。空なら OS の既定のマイクを使います
input_device = ""

# 録音の開始・終了時に効果音を鳴らすか
sound = true

# OS にログインしたときに自動で起動するか
autostart = false

# ログの出力量: "error" / "info" / "debug"
log_level = "info"

# 使うモデルの種類: "small-streaming"（標準）/ "tiny-streaming" / "base"
# base はストリーミング非対応で、話の区切りが確定するまで途中の文字が出ません
# 配布物に入っているのは small-streaming だけです
model_arch = "small-streaming"
# モデルの置き場所。空なら同梱のモデル置き場を使います
model_dir = ""

# 認識結果の置換表。左の文字列を右の文字列に置き換えます
[replace]
# "でぃすこーど" = "Discord"
"""


def write_default(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TEMPLATE.format(hotkey=default_hotkey()), encoding="utf-8")


def load(path: Path) -> Config:
    """設定ファイルを読む。ファイルがなければ標準値のファイルを作る（要件 R6.2）。"""
    if not path.exists():
        write_default(path)
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        cfg = Config()
        cfg.errors.append(f"設定ファイルの書式に誤りがあるため、すべて標準値で動きます: {e}")
        return cfg
    except OSError as e:
        cfg = Config()
        cfg.errors.append(f"設定ファイルを読めないため、すべて標準値で動きます: {e}")
        return cfg
    return parse(raw)


def parse(raw: dict) -> Config:
    cfg = Config()
    errors = cfg.errors

    def take(key: str, expected: type, choices: tuple | None = None, check=None):
        if key not in raw:
            return
        value = raw[key]
        default = getattr(cfg, key)
        # bool は int のサブクラスなので、int の項目に true を書いた誤りを先に弾く
        ok = isinstance(value, expected) and not (expected is int and isinstance(value, bool))
        if ok and choices is not None:
            ok = value in choices
        if ok and check is not None:
            ok = check(value)
        if ok:
            setattr(cfg, key, value)
        else:
            hint = f"（使える値: {', '.join(choices)}）" if choices else ""
            errors.append(f"{key} = {value!r} は使えないため、標準値 {default!r} で動きます{hint}")

    take("hotkey", str, check=_valid_hotkey)
    take("silence_timeout_sec", int, check=lambda v: 1 <= v <= 3600)
    take("insert_method", str, INSERT_METHODS)
    take("restore_clipboard", bool)
    take("input_device", str)
    take("sound", bool)
    take("autostart", bool)
    take("log_level", str, LOG_LEVELS)
    take("model_dir", str)
    take("model_arch", str, MODEL_ARCHS)

    if "replace" in raw:
        table = raw["replace"]
        if isinstance(table, dict):
            for src, dst in table.items():
                if isinstance(dst, str) and src:
                    cfg.replace[src] = dst
                else:
                    errors.append(f"replace の {src!r} = {dst!r} は文字列ではないため、無視します")
        else:
            errors.append("replace は表（[replace]）で書いてください。置換は行いません")

    known = set(Config.__dataclass_fields__) - {"errors"}
    for key in raw:
        if key not in known:
            errors.append(f"{key} という設定項目はないため、無視します")
    return cfg


def _valid_hotkey(value: str) -> bool:
    from moonshine_dictate.hotkey import parse_hotkey

    try:
        parse_hotkey(value)
    except ValueError:
        return False
    return True
