# vast-revenue-monitor

<p align="center">
  <img
    src="https://github.com/user-attachments/assets/098a47d2-8ad1-4c83-81de-55ef7a8cfc94"
    alt="Vast Revenue Monitor Discord notification"
    width="400"
  >
</p>

<p align="center">
  <strong>Vast.aiホストの収益を監視し、Discordへ自動通知する運用向けツール</strong>
</p>

<p align="center">
  <a href="README.md">English</a> | 日本語
</p>

**現在の安定版：v1.1.2**

## 概要

Vast Revenue Monitorは、Vast.aiホストの収益状況を定期的に取得し、Discordへ自動通知する監視サービスです。

直近区間、本日、昨日、今週、今月の収益に加え、週間目標の進捗、USD/JPY換算、ATH（過去最高記録）を表示します。

日次はJST 09:00、週次は土曜日09:00を境界として集計します。Vast.aiの支払リセットが遅れた場合も、実際の残高減少を確認してから週を確定するため、境界時刻のずれによる誤集計を防ぎます。

Python 3.12以降に対応し、systemdサービスとして常時運用できます。Discord通知は日本語と英語に対応しています。

## 主な機能

- Vast.ai収益の定期取得とDiscord Embed通知
- 直近区間、本日、昨日、今週、今月の収益表示
- USD/JPY換算と複数為替プロバイダーによる取得
- 週間収益目標の進捗表示
- Hourly / Daily / Weekly / Monthly ATH
- 簡易レポートと詳細レポート
- 日本語・英語通知
- systemdによる自動起動と常時監視
- 原子的な状態保存
- バックアップ、復元、アンインストール
- 安全な1コマンドアップデート
- 明示的な状態修復機能

## Discord通知の内容

### 簡易レポート

```text
💰 VAST.AI 毎時収益レポート

収益
直近区間 $5.36 / ¥849
本日 $82.31 / ¥13,049
昨日 $124.39 / ¥19,721
今週 $82.31 / ¥13,049
今月 $997.27 / ¥158,105

週間目標
現在: $82.31
目標: $900.00
進捗: 9.1%
目標まで残り: $817.69

ATH
時間: $6.46
日間: $143.98
週間: $914.96
月間: $0.00
```

### 詳細レポート

詳細レポートを有効にすると、次の情報も追加されます。

- 前回通知からの増減額と増減率
- 日間目標の進捗
- 現在の進捗率と期待進捗率
- 目標に対する先行・遅延
- 日間収益の最終予測
- 現在の状態

## 収益期間の定義

すべての境界は、設定されたタイムゾーンを基準にします。既定値は `Asia/Tokyo` です。

| 表示 | 定義 |
|---|---|
| 直近区間 | 最新の正常な取得区間で確認された正の残高差分 |
| 本日 | 当日09:00から現在まで |
| 昨日 | 直前に完了した09:00から翌09:00まで |
| 今週 | 土曜日09:00から現在までの進行中の支払週 |
| 今月 | その月に属する完了支払週と、現在進行中の支払週の合計 |

「直近区間」は60分の移動合計や時間換算レートではありません。前回の正常取得から今回の取得までに実際に増えた金額を表示します。

### 日次

日次期間は次のとおりです。

```text
09:00:00 ～ 翌日08:59:59
```

本日は現在進行中の日次期間です。

昨日は直前に完了した日次期間で、次の09:00まで変化しません。

### 週次

週次期間は次のとおりです。

```text
土曜日09:00:00 ～ 翌週土曜日08:59:59
```

Vast.aiの支払リセットが09:00より遅れる場合があります。

そのため、本ツールは時刻だけで週次リセットを確定しません。土曜日09:00以降に実際の残高減少を確認した時点で、直前の残高を完了週として確定します。

### 月次

月間収益は暦日の単純合計ではなく、Vast.aiの支払週を基準に計算します。

週は、その週が完了した土曜日の属する月へ計上されます。

そのため、月によって支払週が4回または5回になります。これは意図した動作です。

## ATHの定義

ATHはAll Time High、つまり過去最高記録です。

| ATH | 更新条件 |
|---|---|
| Hourly | 有効な直近区間が過去最高を更新したとき |
| Daily | 09:00から翌09:00までの日次期間が完了したとき |
| Weekly | 土曜日から翌土曜日までの支払週が完了したとき |
| Monthly | 支払月が完了したとき |

Hourly ATHは有効な正の `increment` だけから計算します。口座残高そのものは使用しません。

Daily、Weekly、Monthly ATHは、進行中の期間では更新されません。完了した期間だけが比較対象です。

## Ubuntu 24.04 LTSへのインストール

### 事前に準備するもの

- Ubuntu 24.04 LTSサーバ
- `sudo` 権限を持つユーザー
- Discord Webhook URL
- Vast.ai APIキー
- DNSとHTTPS接続が正常に動作する環境

Pythonのインストール、仮想環境の作成、systemd設定はインストーラーが自動で行います。

### リポジトリを取得する

```bash
sudo apt-get update
sudo apt-get install -y git

git clone https://github.com/sakusaku0214/vast-revenue-monitor.git
cd vast-revenue-monitor
```

### インストール前の確認（任意）

ファイルを変更せずに、リポジトリとホスト環境を検証できます。

```bash
sudo bash install.sh --check
```

次のメッセージが表示されれば成功です。

```text
[vast-revenue-monitor] Validation completed; no changes were made.
```

### インストールを実行する

```bash
sudo bash install.sh
```

対話形式で次の情報を入力します。

- Discord Webhook URL
- Vast.ai APIキー
- 週間収益目標
- 詳細レポートの有効・無効
- 通知言語

Webhook URLとAPIキーは画面に表示されず、それぞれ2回入力して確認します。

通知言語の選択例：

```text
Select Discord notification language:
1) English
2) 日本語
Choice [1]:
```

Enterのみで英語を選択します。

インストール中に次の項目を検証します。

- Vast.ai API
- 為替レート取得先
- Discord Webhook
- Python依存関係
- systemdサービス

検証に失敗した場合はインストールを中断し、不完全な状態をロールバックします。

成功すると次のメッセージが表示されます。

```text
[vast-revenue-monitor] Installation completed successfully.
```

## 動作確認

```bash
sudo systemctl is-enabled vast-balance.service
sudo systemctl is-active vast-balance.service
sudo systemctl status vast-balance.service --no-pager
sudo journalctl -u vast-balance.service -n 50 --no-pager
```

`enabled` と `active` が表示されることを確認してください。

### 手動で1回だけ実行する

```bash
sudo -u vast-revenue-monitor \
  /opt/vast-revenue-monitor/.venv/bin/python \
  /opt/vast-revenue-monitor/balance.py \
  --config /opt/vast-revenue-monitor/config.json \
  --once
```

### バージョンを確認する

```bash
sudo /opt/vast-revenue-monitor/.venv/bin/python \
  /opt/vast-revenue-monitor/balance.py \
  --version
```

## 設定変更

インストール後に、週間目標、通知言語、詳細レポート設定を変更できます。

```bash
sudo /opt/vast-revenue-monitor/reconfigure.sh
```

現在値が表示され、Enterでその設定を維持できます。

設定が実際に変更された場合だけ `vast-balance.service` を再起動します。変更後は確認用の通知が1回送信されます。

APIキー、Discord Webhook、未知の設定キー、履歴、状態、記録は変更しません。

## 設定ファイル

設定ファイル：

```text
/opt/vast-revenue-monitor/config.json
```

主な設定項目：

| 設定 | 内容 |
|---|---|
| `weekly_goal_usd` | 週間収益目標 |
| `daily_goal_usd` | 日間収益目標 |
| `language` | `en` または `ja` |
| `detailed_report` | 詳細レポートの有効・無効 |
| `timezone` | 集計に使用するタイムゾーン |
| `state_dir` | 状態・履歴の保存先 |
| `log_dir` | ログの保存先 |

`state_dir` と `log_dir` に相対パスを指定した場合は、実行時のカレントディレクトリではなく、`config.json` のあるディレクトリを基準に解決します。

## 自動インストール（非対話モード）

環境変数で認証情報を渡してインストールできます。

```bash
export DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/.../...'
export VAST_API_KEY='your-vast-api-key'
export NOTIFICATION_LANGUAGE=ja

sudo --preserve-env=DISCORD_WEBHOOK_URL,VAST_API_KEY,NOTIFICATION_LANGUAGE \
  bash install.sh

unset DISCORD_WEBHOOK_URL VAST_API_KEY NOTIFICATION_LANGUAGE
```

`NOTIFICATION_LANGUAGE` を指定しない場合は英語になります。

## アップデート

推奨方法：

```bash
cd ~/vast-revenue-monitor
sudo ./update.sh
```

`update.sh` は次の処理を行います。

- Git作業ツリーの状態確認
- `git fetch --prune`
- fast-forward可能か確認
- ソースコード更新
- 既存のトランザクション型インストーラーを実行
- `config.json`、`state/`、`logs/`を保持
- 更新失敗時にインストール済みアプリをロールバック

更新内容だけ確認する場合：

```bash
sudo ./update.sh --check
```

### 手動アップデート

```bash
git pull --ff-only origin main
sudo bash install.sh
```

単純な `git pull` だけでは、`/opt/vast-revenue-monitor` にインストールされたアプリケーションは更新されません。

## 状態修復

既存の状態ファイルに、旧バージョン由来の誤った週次リセットやATHが残っている場合は、明示的な修復コマンドを使用できます。

### ドライラン

```bash
sudo systemctl stop vast-balance.service

sudo /opt/vast-revenue-monitor/.venv/bin/python \
  /opt/vast-revenue-monitor/balance.py \
  --config /opt/vast-revenue-monitor/config.json \
  --repair-state
```

ドライランでは修正候補を表示するだけで、ファイルは変更しません。

### 修復を適用する

```bash
sudo /opt/vast-revenue-monitor/.venv/bin/python \
  /opt/vast-revenue-monitor/balance.py \
  --config /opt/vast-revenue-monitor/config.json \
  --repair-state \
  --apply
```

適用前に、設定ファイルと状態ディレクトリのタイムスタンプ付きバックアップを作成します。

修復対象：

- 遅延した週次リセットによる誤った全残高加算
- 不正なHourly ATH
- 不正なDaily ATH
- 不正なWeekly ATH
- 不正なMonthly ATH

修復後はサービスを再開します。

```bash
sudo systemctl start vast-balance.service
sudo systemctl is-active vast-balance.service
```

証拠が不足している場合は推測で修正せず、曖昧な候補として報告します。

## Vast.ai APIレスポンス形式のエラー

`VastApiSchemaError` が出た場合、Vast.aiから返されたJSONに、このバージョンが期待する収益フィールドが含まれていません。

通常運用中の完全なレスポンス：

```text
/opt/vast-revenue-monitor/logs/api_response.json
```

インストール中に失敗した場合：

```text
/tmp/vast-revenue-monitor-api_response.json
```

確認例：

```bash
sudo python3 -m json.tool \
  /tmp/vast-revenue-monitor-api_response.json

sudo journalctl \
  -u vast-balance.service \
  -n 100 \
  -l \
  --no-pager
```

これらのファイルには機密情報が含まれる可能性があります。公開しないでください。

## 保存されるデータ

| 種類 | 保存場所 |
|---|---|
| 設定 | `/opt/vast-revenue-monitor/config.json` |
| 状態・履歴 | `/opt/vast-revenue-monitor/state/` |
| ログ | `/opt/vast-revenue-monitor/logs/` |

主な状態ファイル：

- `revenue_events.json`
- `history.json`
- `history-YYYY.csv`
- `records.json`
- `weekly_reset.json`
- `exchange_rate.json`
- `goal.json`

## サービス操作

状態確認：

```bash
sudo systemctl status vast-balance.service
```

再起動：

```bash
sudo systemctl restart vast-balance.service
```

ログをリアルタイム表示：

```bash
sudo journalctl -u vast-balance.service -f
```

直近100件のログ：

```bash
sudo journalctl -u vast-balance.service -n 100 -l --no-pager
```

## バックアップ・復元・アンインストール

### バックアップ

```bash
sudo /opt/vast-revenue-monitor/install.sh --backup
```

### 復元

```bash
sudo /opt/vast-revenue-monitor/install.sh \
  --restore \
  /path/to/vast-revenue-monitor-backup-YYYYMMDD-HHMMSS.tar.gz
```

### アンインストール

```bash
sudo /opt/vast-revenue-monitor/uninstall.sh
```

バックアップには次の機密情報が含まれます。

- Vast.ai APIキー
- Discord Webhook URL
- 収益履歴
- 状態ファイル

バックアップは安全な場所へ保管し、公開しないでください。必要に応じて別途暗号化してください。

## トラブルシューティング

### サービスが起動しない

```bash
sudo systemctl status vast-balance.service --no-pager
sudo journalctl -u vast-balance.service -n 100 -l --no-pager
```

### アプリケーションログ

```text
/opt/vast-revenue-monitor/logs/vast-revenue-monitor.log
```

### 設定変更後に起動しない

```bash
sudo python3 -m json.tool \
  /opt/vast-revenue-monitor/config.json

sudo systemctl restart vast-balance.service
```

### 通知が届かない

次を確認してください。

- Discord Webhook URLが有効か
- Vast.ai APIキーが有効か
- サービスが `active` か
- DNSとHTTPS接続が正常か
- journalctlにエラーが出ていないか

## セキュリティ

- `config.json` を公開しないでください
- Discord Webhook URLを公開しないでください
- Vast.ai APIキーを公開しないでください
- `api_response.json` を公開しないでください
- バックアップファイルを公開しないでください

漏洩が疑われる場合は、Discord WebhookとVast.ai APIキーの両方をローテーションしてください。

サービスは専用ユーザーで動作します。

## 免責事項

本ソフトウェアは無保証で提供されます。

表示される収益はVast.ai APIの観測値から算出した参考値です。必要に応じてVast.ai公式の値と照合してください。

本ソフトウェアは会計、税務、投資、金融に関する助言を提供するものではありません。

## ライセンス

このプロジェクトはMIT Licenseで公開されています。
