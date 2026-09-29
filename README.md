# PersonalHub

個人用途のさまざまなデータ・ツールを一つにまとめるための Flask ベースのWebアプリケーションです。

メディア管理、YouTube関連機能、Markdown / Obsidian連携、Google Calendar連携、メール・天気情報の取得など、日常的に使用する複数の機能をAPIを中心に統合しています。

---

## Overview

PersonalHub は、個人開発で使用する複数のツールやサービスを一つのアプリケーションから利用できるようにすることを目的としています。

主な役割は以下の通りです。

* ローカルに保存した動画・音楽の管理
* YouTube動画・ライブ配信関連機能
* 動画・音声へのコメント管理
* コメントや各種情報のMarkdownへの出力
* Obsidianのノート管理
* Google Calendarとの連携
* 天気情報の取得
* メールの監視
* 個人用API操作画面
* 定期的なバックグラウンド処理

PersonalHub 自体ですべての処理を実装するのではなく、必要に応じて外部ライブラリや独立したプロジェクトを利用する構成を採用しています。

---

## Features

### Media Management

ローカルに保存した動画・音声ファイルを管理します。

* 動画管理
* 音楽管理
* ファイル情報のデータベース管理
* ファイル名・表示名の管理
* YouTubeからの動画・音声ダウンロード
* 動画・音声のトリミング

メディア情報は SQLite で管理しています。

---

### YouTube

YouTube関連の機能を提供します。

* YouTube Data API の利用
* 動画情報の取得
* チャンネル情報の取得
* YouTube動画のダウンロード
* YouTubeライブ関連機能
* YouTube APIデータのキャッシュ

YouTube Data APIについては、APIクォータの消費を抑えるため、取得したデータをデータベースに保存して再利用する設計を採用しています。

YouTube関連の共通処理は、外部ライブラリである `myutils` および独立プロジェクト `youtube-live-chat-collector` と連携しています。

---

### Comments

動画・音声に対するコメントを管理します。

コメントには以下の情報を保存します。

* コメント本文
* 投稿者
* 対象メディア
* メディアID
* 作成日時
* メディア種別

保存したコメントはMarkdownファイルとして出力することもできます。

---

### Markdown / Obsidian

個人的なノート管理のため、MarkdownおよびObsidianとの連携機能を提供しています。

主な機能：

* Daily Noteの作成
* Weekly Noteの作成
* コメントまとめのMarkdown出力
* Thino関連処理
* ノートへの各種データ出力

Markdown関連の共通処理は外部ライブラリ `myutils` を利用しています。

---

### Google Calendar

Google Calendarから予定情報を取得し、PersonalHub内の処理から利用できるようにしています。

---

### Weather

天気情報を取得し、APIや定期ジョブから利用できます。

---

### Email Monitoring

メールを定期的に確認し、必要な情報をPersonalHub側で処理します。

---

### DevTools

個人開発で使用する補助ツールを `devtools/` にまとめています。

現在は主に以下の機能があります。

* Windowsクリップボード操作
* コードのクリップボードコピー
* ファイルツリーの生成・コピー

これらはPersonalHubの通常のアプリケーション機能とは分離し、開発・運用を補助する目的で使用しています。

---

## Architecture

PersonalHubは、Flaskを中心としたバックエンドとして構成されています。

```text
PersonalHub
│
├── Flask Application
│   ├── API
│   ├── Media Management
│   ├── YouTube
│   ├── Comments
│   ├── Markdown
│   ├── Calendar
│   ├── Clipboard
│   └── Scheduler
│
├── SQLite
│   └── Application Data
│
├── myutils
│   └── 共通ライブラリ
│
└── youtube-live-chat-collector
    └── YouTube Live Chat関連処理
```

依存関係は基本的に一方向になるようにしています。

```text
PersonalHub
    │
    ├──────────────→ myutils
    │
    └──→ youtube-live-chat-collector
                    │
                    └──→ myutils
```

これにより、`youtube-live-chat-collector` はPersonalHubから独立したプロジェクトとしても利用できます。

---

## Project Structure

現在の主要なディレクトリ構成は以下の通りです。

```text
PersonalHub/
│
├── app/
│   ├── media/
│   │   ├── ...
│   │
│   ├── notes/
│   │   ├── ...
│   │
│   ├── static/
│   ├── templates/
│   │
│   ├── views/
│   │   └── api/
│   │       ├── calendar_api.py
│   │       ├── clipboard_api.py
│   │       ├── comment_api.py
│   │       ├── markdown_api.py
│   │       ├── media_api.py
│   │       └── youtube_api_view.py
│   │
│   ├── youtube/
│   │   ├── ...
│   │
│   ├── __init__.py
│   ├── models.py
│   ├── mail.py
│   ├── scheduler.py
│   ├── utils.py
│   └── weather.py
│
├── devtools/
│   ├── clipboard/
│   │   └── windows.py
│   ├── code_copy.py
│   └── file_tree.py
│
├── tests/
│
├── .env
├── requirements.txt
└── README.md
```

※ 実際のプロジェクト構成に合わせて随時更新します。

---

## Scheduler

定期的に実行する処理にはスケジューラを利用しています。

主な定期処理：

* Daily Note作成
* Weekly Note作成
* コメントのMarkdown出力
* Thino関連処理
* メールチェック
* 天気情報の取得
* その他の定期処理

Scheduler関連の処理は、Markdown関連のジョブとその他のジョブを分離して管理しています。

```text
Scheduler
│
├── Markdown Jobs
│   ├── Daily Note
│   ├── Weekly Note
│   ├── Comments
│   └── Thino
│
└── Other Jobs
    ├── Email
    ├── Weather
    └── Other periodic tasks
```

---

## API

PersonalHubでは、Reactなどのフロントエンドから利用するAPIに加えて、個人用途で直接操作するためのAPIも提供しています。

主なAPIカテゴリ：

```text
/api/
├── videos
├── musics
├── comments
├── youtube
├── markdown
├── calendar
├── clipboard
└── ...
```

例えば、開発用API操作画面から以下のような処理を実行できます。

* Daily Note作成
* Weekly Note作成
* Vocabulary関連処理
* Weather取得
* Calendar取得
* クリップボード操作
* ファイルツリーのコピー

---

## Database

アプリケーションのデータ保存には SQLite を使用しています。

主なテーブル：

```text
videos
musics
comments
vocabulary
```

メディア情報やコメントなど、PersonalHubで扱う個人的なデータを保存します。

データベースのパスは環境変数 `DB_PATH` から指定します。

---

## Requirements

主な使用技術：

* Python
* Flask
* SQLAlchemy
* SQLite
* APScheduler
* Google APIs
* YouTube Data API
* FFmpeg
* React（フロントエンド側）
* Obsidian / Markdown

また、共通処理の一部に個人開発ライブラリ `myutils` を利用しています。

---

## Setup

### 1. Repositoryを取得

```bash
git clone <repository-url>
cd PersonalHub
```

### 2. 仮想環境を作成

```bash
python -m venv .venv
```

### 3. 仮想環境を有効化

Windows:

```bash
.venv\Scripts\activate
```

### 4. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

### 5. 環境変数を設定

`.env` またはシステム環境変数に必要な値を設定します。

例：

```env
DB_PATH=path/to/personalhub.db

DAILY_NOTE_DIR=path/to/daily_notes
WEEKLY_NOTE_DIR=path/to/weekly_notes
PLAN_NOTE_DIR=path/to/plan_notes
WEEKLY_NOTE_TEMPLATE=path/to/template.md

YOUTUBE_DB_PATH=path/to/youtube.db
```

Google APIやYouTube APIなど、利用する機能によって追加の設定が必要です。

---

## Running

開発環境ではFlaskアプリケーションを起動します。

```bash
flask run
```

または、プロジェクトで使用している起動方法に合わせて実行します。

---

## Testing

テストには `pytest` を使用します。

```bash
pytest
```

特定のテストだけ実行する場合：

```bash
pytest tests/...
```

---

## Development Policy

PersonalHubは個人開発プロジェクトですが、機能追加によってコードが複雑化しないよう、以下のような方針で開発しています。

### 機能ごとの分離

API、メディア処理、YouTube処理、Markdown処理、Schedulerなどを可能な限り分離します。

### 共通処理のライブラリ化

PersonalHub固有ではない汎用的な処理は、可能な限り `myutils` などの共通ライブラリへ切り出します。

### 独立プロジェクトとの分離

YouTube Live Chat Collectorなど、単独でも利用できる機能は独立したプロジェクトとして管理します。

### テスト

リファクタリングや機能追加の際には、pytestによるテストを追加・更新し、既存機能への影響を確認します。

---

## Git Branch Strategy

開発中の機能は `feature/*` ブランチで作業し、完成した機能を `main` に統合します。

```text
main
 │
 ├── feature/scheduler
 ├── feature/devtools
 ├── feature/youtube-api
 └── feature/markdown
```

基本的な開発フロー：

```bash
git switch main
git pull --ff-only

git switch -c feature/new-feature

# 開発

git add .
git commit -m "feat: 新機能を追加"

# 完成後 main に統合
git switch main
git merge feature/new-feature
git push
```

機能開発中に `main` が更新された場合は、必要に応じてfeatureブランチへ取り込みます。

```bash
git switch main
git pull --ff-only

git switch feature/new-feature
git merge main
```

---

## Project Status

PersonalHubは現在も開発中です。

今後も以下のような方向で機能を整理・拡張していく予定です。

* API構成の整理
* YouTube関連機能の整理
* Schedulerの拡張
* Markdown / Obsidian連携の改善
* メディア管理機能の改善
* テストの拡充
* 共通処理のライブラリ化
* 外部プロジェクトとの責務分離

---

## License

個人利用を目的としたプロジェクトです。
