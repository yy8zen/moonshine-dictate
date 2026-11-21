"""認識したテキストを、フォーカスのあるウィンドウに入れる（要件 R5）。"""

from __future__ import annotations

from typing import Callable, Protocol

from moonshine_dictate.platform_info import IS_MACOS, is_wayland


class Inserter(Protocol):
    # True なら確定した区切りごとに insert() を呼ぶ。False なら録音の終了時に全文で1回呼ぶ
    live: bool

    def insert(self, text: str) -> None: ...


def create(method: str, restore_clipboard: bool,
           wait_keys_released: Callable[[], None], notify: Callable[[str], None]) -> Inserter:
    """設定と実行環境に合う挿入方法を返す。

    wait_keys_released: ホットキーの修飾キーが離されるまで待つ関数。押されたまま Ctrl+V を送ると
    Ctrl+Alt+V などの別のショートカットになるため、送る前に呼ぶ。
    notify: 利用者への通知を出す関数。
    """
    if is_wayland():
        from moonshine_dictate.insert.wayland import WaylandInserter

        if method == "live":
            notify("Wayland ではライブ入力を使えないため、クリップボードで入力します")
        return WaylandInserter(notify)
    from moonshine_dictate.insert.clipboard import ClipboardInserter

    if method == "live":
        if not IS_MACOS:
            # Windows と Linux では、日本語を1文字ずつキー入力として送ると文字が化ける。
            # - Windows: 日本語 IME がオンのとき、「もう次に進んでも大丈夫ですよ」が
            #   「もうんでもですよ大丈夫次進」になった（2026年11月、Windows 11 の実機）
            # - Linux（X11）: XTest で「こんにちは、世界。」が「こんんちはは世界界」になった（Xvfb 上の検証）
            # そのため、確定した区切りごとにクリップボード経由で貼り付ける
            return ClipboardInserter(restore_clipboard, wait_keys_released, live=True)
        from moonshine_dictate.insert.live import LiveInserter

        return LiveInserter(wait_keys_released)
    return ClipboardInserter(restore_clipboard, wait_keys_released)
