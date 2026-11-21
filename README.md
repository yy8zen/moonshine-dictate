# moonshine-dictate
Moonshine Voiceを使った、Windows・macOS・Linux対応のローカル音声入力ツール。

ホットキーを押すと録音が始まり、話した日本語がフォーカスのあるアプリに入力されます。操作は Windows 11 の音声入力（Win+H）に合わせています。音声認識はすべて PC の中で行い、ネットワーク通信は一切しません。

## インストールして起動する

配布ファイルは GitHub の [Releases](https://github.com/yy8zen/moonshine-dictate/releases) からダウンロードします。まだリリースがない間は、[Actions](https://github.com/yy8zen/moonshine-dictate/actions/workflows/build.yml) の最新の成功した実行を開き、Artifacts から自分の OS の zip をダウンロードして展開してください（GitHub へのログインが必要です）。

### Windows

1. `moonshine-dictate-<バージョン>-windows-setup.exe` を実行します。管理者権限は要りません。`%LOCALAPPDATA%\Programs\moonshine-dictate` にインストールされます。
2. 「Windows によって PC が保護されました」と表示されたら、「詳細情報」を押してから「実行」を押します。配布ファイルに電子署名がないため表示されます。
3. インストールの最後の画面で「moonshine-dictate を起動する」にチェックを入れたまま「完了」を押すと起動します。次からはスタートメニューの「moonshine-dictate」から起動します。

**スマート アプリ コントロールがオンの PC では動かない場合があります。** 配布ファイルに電子署名がないため、「アプリケーション制御ポリシーによってこのファイルがブロックされました」と表示され、インストーラーやアプリが止められることがあります。初めて実行したときだけ止められ、もう一度実行すると動く場合もあります。何度実行しても止められる場合は、ファイルを個別に許可する方法はありません。「Windows セキュリティ > アプリとブラウザーの制御 > スマート アプリ コントロール」をオフにするしかありません。会社が管理する PC では、管理者に相談してください。

### macOS（Apple Silicon）

1. `moonshine-dictate-<バージョン>-macos-arm64.dmg` を開き、`moonshine-dictate.app` を「アプリケーション」フォルダにドラッグします。
2. 「アプリケーション」フォルダで moonshine-dictate を右クリックして「開く」を選びます。macOS 15 以降でこの方法では開けない場合は、一度ダブルクリックして警告を閉じてから、「システム設定 > プライバシーとセキュリティ」の下にある「このまま開く」を押します。配布ファイルが Apple の署名と公証を受けていないため、この手順が要ります。
3. マイクとアクセシビリティの許可を求められたら、許可します（[macOS の注意](#macos)を参照）。
4. Dock にはアイコンが出ません。メニューバーにマイクのアイコンが出れば起動しています。

### Linux

1. `moonshine-dictate-<バージョン>-linux-x86_64.AppImage` に実行権限を付けて、実行します。

   ```
   chmod +x moonshine-dictate-*-linux-x86_64.AppImage
   ./moonshine-dictate-*-linux-x86_64.AppImage
   ```

2. 「libfuse.so.2 が見つからない」というエラーで起動しない場合は、FUSE 2 のライブラリを入れてください。Ubuntu 24.04 では `sudo apt install libfuse2t64`、22.04 では `sudo apt install libfuse2` です。

### 起動・終了・自動起動

- 起動すると、モデルを読み込む間はトレイのアイコンが黄色になり、使えるようになると灰色になります。
- すでに起動している状態でもう一度起動すると、「すでに起動しています」と表示して終わります。2つ同時には動きません。
- 終了するときは、トレイのアイコンのメニューから「終了」を選びます。
- ログインしたときに自動で起動させるには、設定ファイルで `autostart = true` にして、「設定の再読み込み」を選びます。

### ソースコードから起動する

Python 3.11 以降が必要です。

```
git clone https://github.com/yy8zen/moonshine-dictate.git
cd moonshine-dictate
python -m pip install -e .
python scripts/fetch_model.py      # 日本語モデル（約120MB）を models/ にダウンロードする。最初の1回だけ
python -m moonshine_dictate        # 起動する
```

## 使い方

1. アプリを起動すると、タスクトレイ（macOS ではメニューバー）にマイクのアイコンが出ます。アイコンが灰色になったら使えます。モデルを読み込んでいる間は黄色です。
2. 文字を入れたい場所をクリックしてから、**Ctrl+Alt+Space**（macOS では **Control+Option+Space**）を押します。画面の下に録音ウィンドウが出て、マイクのボタンが赤く点灯します。
3. 話します。認識中の文字は録音ウィンドウに表示されます。
4. 次のどれかで録音が終わります。
   - もう一度ホットキーを押す
   - 録音ウィンドウのマイクのボタンを押す
   - 無音が60秒続く

テキストの入れ方は2種類あり、設定ファイルで選べます。

| 設定値 | 入るタイミング | 方法 |
| --- | --- | --- |
| `clipboard`（標準） | 録音の終了時に全文 | クリップボードに入れて Ctrl+V（macOS は Cmd+V）を送る。貼り付けの後、元のクリップボードの内容に戻す |
| `live` | 話の区切りが確定するたび | Windows と Linux はクリップボード経由で区切りごとに貼り付ける。macOS はキー入力として送る |

コマンドラインからも操作できます。OS のショートカットキーに割り当てる場合などに使います。

```
moonshine-dictate toggle   # 録音の開始・終了を切り替える（start / stop / reload / quit も使える）
```

`moonshine-dictate` の部分は、OS ごとに次のパスに置き換えてください。

| OS | コマンドのパス |
| --- | --- |
| Windows | `"%LOCALAPPDATA%\Programs\moonshine-dictate\moonshine-dictate.exe"` |
| macOS | `/Applications/moonshine-dictate.app/Contents/MacOS/moonshine-dictate` |
| Linux | AppImage のファイルのパス（例：`~/Applications/moonshine-dictate-0.1.0-linux-x86_64.AppImage`） |
| ソースコードから | `python -m moonshine_dictate` |

## 設定ファイル

初回の起動時に、次の場所に標準値の設定ファイルが作られます。各項目の説明はファイルの中にコメントで書いてあります。トレイのメニューから「設定ファイルを開く」で開けます。編集した後は「設定の再読み込み」で反映されます。

| OS | 場所 |
| --- | --- |
| Windows | `%APPDATA%\moonshine-dictate\config.toml` |
| macOS | `~/Library/Application Support/moonshine-dictate/config.toml` |
| Linux | `~/.config/moonshine-dictate/config.toml` |

設定できる項目は、ホットキー、無音で終了するまでの秒数、テキストの入れ方、クリップボードを元に戻すか、マイクのデバイス、効果音、ログイン時の自動起動、ログの出力量、認識結果の置換表です。ログは設定ファイルと同じフォルダの `moonshine-dictate.log` に出ます。

## OS ごとの注意

### macOS

配布しているアプリは Apple の署名と公証を受けていません。

- 初回の開き方は[インストールして起動する](#macosapple-silicon)を参照してください。ダブルクリックだけでは警告が出て開けません。
- 「システム設定 > プライバシーとセキュリティ」で、**マイク**と**アクセシビリティ**を許可してください。アクセシビリティは、ホットキーの検出とテキストの入力に使います。
- アップデートした後にホットキーが効かなくなったら、アクセシビリティの一覧から moonshine-dictate を一度削除して、もう一度許可してください。

### Linux（X11）

すべての機能が使えます。AppImage を使わずに動かす場合、Ubuntu では `libxcb-cursor0` と `libportaudio2` が必要です。

### Linux（Wayland）

Wayland では、セキュリティの仕組み上、ほかのアプリのキー入力を監視できません。そのため次の制限があります。

- ホットキーはアプリでは登録しません。OS の設定でショートカットキーを追加し、コマンド `moonshine-dictate toggle` を割り当ててください（GNOME では「設定 > キーボード > ショートカットを表示およびカスタマイズ > カスタムショートカット」）。
- テキストは `wl-copy`（パッケージ名 `wl-clipboard`）でクリップボードに入れ、`ydotool` があれば Ctrl+V を送ります。`ydotool` がない場合は、通知が出たら自分で Ctrl+V を押してください。
- ライブ入力は使えず、クリップボード方式で動きます。

## 開発

```
python -m pip install -e ".[dev]"
python scripts/fetch_model.py      # 同梱する日本語モデルを models/ にダウンロードする
python -m moonshine_dictate        # 起動する
python -m pytest                   # テスト（Linux では xvfb-run -a python -m pytest）
pyinstaller packaging/moonshine-dictate.spec   # 配布用に固める
```

要件は [docs/requirements.md](docs/requirements.md) にまとめています。配布物は GitHub Actions（`.github/workflows/build.yml`）で作ります。`v` で始まるタグを push すると、Windows のインストーラー、macOS の dmg（Apple Silicon 版のみ）、Linux の AppImage をリリースの下書きに添付します。

## 📄 ライセンス

### ソースコード
このリポジトリに含まれるソースコードは [MIT License](LICENSE) の下で公開されています。

### 配布バイナリ・音声認識モデルについて
リリースページ等で配布している実行ファイル（`.exe` / `.dmg` / `.AppImage`）には、Moonshine AIの日本語音声認識モデルが同梱されています。  
そのため、同梱モデルおよびモデルを含む配布パッケージの利用には **[Moonshine Community License](https://www.moonshine.ai/license)** が適用されます。

- 配布パッケージは無料です。
- 商用目的での利用の条件は、[ライセンス全文](https://www.moonshine.ai/license)をご確認ください。
