import pytest

from moonshine_dictate import insert


@pytest.mark.parametrize("is_macos, expected", [(False, "ClipboardInserter"), (True, "LiveInserter")])
def test_live_method_per_os(qapp, monkeypatch, is_macos, expected):
    monkeypatch.setattr(insert, "IS_MACOS", is_macos)
    monkeypatch.setattr(insert, "is_wayland", lambda: False)
    if expected == "LiveInserter":
        # pynput の Controller は X サーバーがないと作れないので、偽物に差し替える
        import moonshine_dictate.insert.live as live

        monkeypatch.setattr(live, "LiveInserter",
                            type("LiveInserter", (), {"live": True,
                                                      "__init__": lambda self, w: None}))
    inserter = insert.create("live", True, lambda: None, lambda m: None)
    assert type(inserter).__name__ == expected
    assert inserter.live is True


def test_clipboard_method_is_not_live(qapp, monkeypatch):
    monkeypatch.setattr(insert, "is_wayland", lambda: False)
    inserter = insert.create("clipboard", True, lambda: None, lambda m: None)
    assert inserter.live is False
