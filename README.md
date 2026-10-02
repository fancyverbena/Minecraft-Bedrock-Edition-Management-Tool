# Minecraft Bedrock Edition Updater

Minecraft Bedrock Edition（統合版）のアップデート管理・バージョンダウングレードを、シンプルなコマンドライン画面から操作できるツールです。  
GDK版への移行に伴う「起動時の強制自動更新」を **Pyroclastic** でバイパスし、任意のバージョンを維持できるようにします。

## 主な機能

- 🔄 **最新バージョンの自動チェックと更新**  
  起動時に最新版を確認し、必要に応じて Onix Client のミラーからインストール
- ⬇️ **任意バージョンへのダウングレード**  
  ページング対応のバージョン一覧から選択してインストール
- 🛡️ **Pyroclastic による自動更新バイパス**  
  GDK版 Minecraft の強制更新を無効化し、ダウングレード後のバージョンを維持
- 🌏 **多言語対応**（日本語・英語・韓国語・簡体中文）

## インストール

### リリースからインストール

1. [Releases](https://github.com/fancyverbena/Minecraft-Bedrock-Edition-Management-Tool/releases) から最新の実行ファイルをダウンロード
2. ダウンロードした `Minecraft_Bedrock_Updater.exe` を **管理者として実行**

> ⚠️ 管理者権限が必須です。UAC の昇格プロンプトが表示されたら承認してください。

### ソースから実行

```powershell
pip install requests pywin32 tqdm pycryptodome
python "Minecraft Bedrock updater.py"
```

## 使い方

起動すると、最新版の自動チェックが走ります。新バージョンがあれば更新するかどうかを確認します。

```text
========== Minecraft Bedrock Edition Updater ==========
0: 終了
1: アップデートチェック
2: バージョンダウングレード
3: Pyroclastic のインストール / アンインストール (自動更新バイパス)
4: 言語設定

選択 (0-4):
```

## 各メニューの説明

| # | 機能 | 説明 |
| :--- | :--- | :--- |
| **1** | アップデートチェック | 現在のバージョンと最新版を比較。更新があれば自動更新または Store を開けます|
| **2** | バージョンダウングレード | 任意のバージョンに変更。Pyroclastic が未導入なら自動で導入されます|
| **3** | Pyroclastic の管理 | 自動更新バイパスのインストール/アンインストール/状態確認|
| **4** | 言語設定 | 表示言語を切り替え（設定は `config.json` に保存）|

## 典型的な操作フロー

### 初回セットアップ

1. `Minecraft Bedrock updater.exe` を管理者として実行
2. UACを承認
3. メニュー **4** で日本語に切り替え
4. メニュー **3** → `1` で Pyroclastic をインストール
5. 以降は Minecraft を通常起動しても自動更新されなくなります

### 特定バージョンへのダウングレード

1. メニュー **2** を選択
2. 警告を確認して `y`
3. Pyroclastic が未導入なら自動インストール
4. バージョン一覧から希望の番号を選択（`n` / `p` でページ送り、`q` でキャンセル）
5. インストール方法を選択
   * `1`: 自動インストール（推奨）
   * `2`: 手動インストール
   * `3`: アンインストール → 自動インストール
6. 完了後、Pyroclastic が自動的に再適用されます

## Pyroclastic について

Pyroclastic は、GDK版 Minecraft が起動時に実行する **PC Bootstrapper**（強制更新チェック）をバイパスするための DLL です。

* **仕組み**: `gamelaunchhelper.dll` を Minecraft のインストールフォルダに配置することで、Gaming Runtime Services の起動チェックをスキップします
* **公式リポジトリ**: Aetopia/Pyroclastic
* **配置先の例**: `C:\XboxGames\Minecraft for Windows\Content\gamelaunchhelper.dll`

> **なぜ必要か**
> Minecraft 1.21.120 以降、統合版は UWP 形式から GDK 形式に移行しました。GDK 版は起動時に必ず最新版かどうかを確認し、古い場合は強制更新を促します。従来の `AutoUpdatePolicy` レジストリや `AutoDownload` ポリシーでは、この GDK の起動チェックを止められません。Pyroclastic はこの根本的な仕組みを回避します。

## アンインストール方法

メニュー **3** から `2` を選択すると `gamelaunchhelper.dll` を削除します。
手動で削除したい場合は、Minecraft のインストールフォルダから `gamelaunchhelper.dll` を消してください。

## データの保存場所

Minecraft のバージョンによってセーブデータの場所が異なります。

| バージョン | パス |
| :--- | :--- |
| **1.21.113 以前 (UWP版)** | `%LOCALAPPDATA%\Packages\Microsoft.MinecraftUWP_8wekyb3d8bbwe\LocalState\games\com.mojang`|
| **1.21.120 以降 (GDK版)** | `%APPDATA%\Minecraft Bedrock\Users\<ID>\games\com.mojang`|

> 💡 **GDK版への移行時の注意**
> バージョンアップに伴いセーブデータの保存先が変わります。事前に旧フォルダを手動でバックアップしておくことを推奨します。

## 注意事項

* 本ツールは**非公式**です
* バージョン変更や Pyroclastic の導入は**自己責任**で行ってください
* **Microsoft** や **Mojang**、**Onix Client** とは関係ありません
* オンラインサーバーへ接続する場合、古いバージョンでは **Outdated Client** エラーで拒否されることがあります（シングルプレイやローカル用途を推奨）
* バグ報告や機能要望は Issues で受け付けます
* サポートコミュニティ: https://discord.gg/dqvmWNkFBa

## 動作環境

* Windows 10 / 11 (x64)
* Python 3.9 以上（ソースから実行する場合）
* 管理者権限
* インターネット接続（バージョン取得・ダウンロードのため）

## ライセンス

このプロジェクトは MIT ライセンス の下で公開されています。