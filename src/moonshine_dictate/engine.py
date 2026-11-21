"""マイク入力と Moonshine のストリーミング認識（要件 R2）。

マイクのコールバックは音声をキューに入れるだけにし、認識は専用のスレッドで行う。
認識結果は Qt のシグナルで UI スレッドに渡す（シグナルはスレッドをまたいでも安全に届く）。
"""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from moonshine_dictate.platform_info import resource_root

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000
BLOCK_FRAMES = 1024

# model_arch の設定値 → 同梱ディレクトリ名と ModelArch の名前
MODEL_DIRS = {
    "small-streaming": ("small-streaming-ja", "SMALL_STREAMING"),
    "tiny-streaming": ("tiny-streaming-ja", "TINY_STREAMING"),
    # ストリーミング非対応。区切りが確定するまで途中結果は出ないが、Small Streaming より大きい
    "base": ("base-ja", "BASE"),
}
BUNDLED_ARCH = "small-streaming"


@dataclass
class ModelSpec:
    path: Path
    arch_name: str


def resolve_model(model_dir: str, model_arch: str) -> ModelSpec:
    """使うモデルの場所を決める。

    model_dir が空なら、同梱のモデル置き場（models/）から model_arch のモデルを探す（要件 R2.2）。
    配布物に入っているのは small-streaming だけなので、ほかの種類は開発時に
    scripts/fetch_model.py でダウンロードしたものを使う。
    """
    dirname, arch_name = MODEL_DIRS[model_arch]
    if model_dir:
        return ModelSpec(Path(model_dir).expanduser(), arch_name)
    return ModelSpec(resource_root() / "models" / dirname, arch_name)


def find_input_device(name: str):
    """設定のデバイス名（部分一致）からデバイス番号を返す。空なら None（OS の既定）。"""
    if not name:
        return None
    import sounddevice as sd

    needle = name.lower()
    for index, dev in enumerate(sd.query_devices()):
        if dev.get("max_input_channels", 0) > 0 and needle in dev.get("name", "").lower():
            return index
    raise LookupError(f"マイク {name!r} が見つかりません")


class Engine(QObject):
    """認識エンジン。`load()` の後、`start()` と `stop()` を繰り返し呼べる。"""

    loaded = Signal()
    load_failed = Signal(str)
    # 認識中の区切りの途中結果（line_id, text）。録音ウィンドウの表示に使う（要件 R4.4）
    line_changed = Signal(object, str)
    # 確定した区切り（line_id, text）（要件 R2.7）
    line_completed = Signal(object, str)
    # 発話を検出した。無音タイムアウトの計測をやり直すのに使う（要件 R3.2）
    activity = Signal()
    # stop() の後、残りの音声の認識が終わった
    finished = Signal()
    failed = Signal(str)

    _STOP = object()

    def __init__(self) -> None:
        super().__init__()
        self._transcriber = None
        self._commands: queue.Queue = queue.Queue()
        self._audio_stream = None
        self._worker = threading.Thread(target=self._run, name="moonshine-engine", daemon=True)
        self._worker.start()

    # ---- UI スレッドから呼ぶ ----

    def load(self, spec: ModelSpec) -> None:
        self._commands.put(("load", spec))

    @property
    def is_loaded(self) -> bool:
        return self._transcriber is not None

    def start(self, device_name: str) -> None:
        import sounddevice as sd

        device = find_input_device(device_name)
        self._commands.put(("begin", None))
        try:
            self._audio_stream = self._open_stream(sd, device)
        except Exception:
            self._commands.put(("end", None))
            raise

    def stop(self) -> None:
        if self._audio_stream is not None:
            try:
                self._audio_stream.stop()
                self._audio_stream.close()
            finally:
                self._audio_stream = None
        self._commands.put(("end", None))

    def shutdown(self) -> None:
        self.stop()
        self._commands.put(("quit", None))

    # ---- マイク ----

    def _open_stream(self, sd, device):
        def callback(indata, frames, time_info, status):  # PortAudio のスレッド
            if status:
                log.debug("マイク入力の状態: %s", status)
            self._commands.put(("audio", (indata[:, 0].copy(), rate)))

        try:
            rate = SAMPLE_RATE
            stream = sd.InputStream(samplerate=rate, blocksize=BLOCK_FRAMES, device=device,
                                    channels=1, dtype="float32", callback=callback)
        except Exception:
            # 16kHz を受け付けないデバイスでは、デバイス本来のレートで録って Moonshine に変換させる
            rate = int(sd.query_devices(device, "input")["default_samplerate"])
            stream = sd.InputStream(samplerate=rate, blocksize=BLOCK_FRAMES, device=device,
                                    channels=1, dtype="float32", callback=callback)
        stream.start()
        return stream

    # ---- 認識スレッド ----

    def _run(self) -> None:
        stream = None
        while True:
            command, payload = self._commands.get()
            try:
                if command == "load":
                    self._load(payload)
                elif command == "begin":
                    stream = self._begin()
                elif command == "audio" and stream is not None:
                    audio, rate = payload
                    stream.add_audio(audio.tolist(), rate)
                elif command == "end" and stream is not None:
                    stream.stop()  # 残りの音声を認識し、最後のイベントを出す
                    stream.close()
                    stream = None
                    self.finished.emit()
                elif command == "quit":
                    return
            except Exception as e:  # pragma: no cover - ネイティブ側の失敗
                log.exception("認識でエラーが起きました")
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
                    stream = None
                self.failed.emit(str(e))
                self.finished.emit()

    def _load(self, spec: ModelSpec) -> None:
        try:
            from moonshine_voice import ModelArch, Transcriber

            if not spec.path.is_dir():
                raise FileNotFoundError(f"モデルが見つかりません: {spec.path}")
            self._transcriber = Transcriber(str(spec.path), ModelArch[spec.arch_name])
        except Exception as e:
            log.exception("モデルの読み込みに失敗しました")
            self.load_failed.emit(str(e))
            return
        log.info("モデルを読み込みました: %s", spec.path)
        self.loaded.emit()

    def _begin(self):
        if self._transcriber is None:
            raise RuntimeError("モデルを読み込んでいません")
        from moonshine_voice import LineCompleted, LineStarted, LineTextChanged

        stream = self._transcriber.create_stream()

        def listener(event) -> None:
            line = getattr(event, "line", None)
            if line is None:
                if hasattr(event, "error"):
                    log.error("認識のエラー: %s", event.error)
                return
            if isinstance(event, (LineStarted, LineTextChanged)):
                self.activity.emit()
                self.line_changed.emit(int(line.line_id), line.text or "")
            elif isinstance(event, LineCompleted):
                self.activity.emit()
                self.line_completed.emit(int(line.line_id), line.text or "")

        stream.add_listener(listener)
        stream.start()
        return stream
