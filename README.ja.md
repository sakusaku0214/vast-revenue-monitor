# vast.ai-revenue-monitor

<img width="400" alt="image" src="https://github.com/user-attachments/assets/098a47d2-8ad1-4c83-81de-55ef7a8cfc94" />

[English](README.md) | 日本語

**現在の安定版: v1.1.0**

## 概要

Vast.aiホスト向けの収益監視・Discord通知ツールです。Vast.ai APIから収益情報を定期的に取得し、時間・日・週・月ごとの収益や最高記録、目標の進捗をDiscord Embedで通知します。

Python 3.12以降に対応した本番運用向けのサービスです。日本語と英語の両方の通知に対応しています。

## 主な機能

- 直近区間（英語表示では Hourly）、本日、今週、今月の収益を通知
- USD/JPY の為替レートを複数のプロバイダーから取得し、永続キャッシュを利用
- 週間目標の進捗管理と最高記録の更新通知
- 詳細レポート、GPU/API 警告
- 土曜日 09:00 JST 付近での週間リセット
- 履歴・状態の原子的な保存
- 通知言語：英語 (`en`) / 日本語 (`ja`)

「直近区間」は、最新の正常な観測で得られた正の増加額そのものです。60分の移動合計でも、時間換算・補正したレートでもありません。短い手動区間や遅延があった場合も、実際の増加額を表示します。

## Ubuntu 24.04 LTSへのインストール

### 事前に準備するもの

以下が必要です。

- Ubuntu 24.04 LTS サーバ（DNS と HTTPS 接続が動作していること）
- `sudo` 権限を持つユーザー
- Discord Webhook URL（通知先チャンネル用）
- Vast.ai API キー

Python のインストールや仮想環境の作成、systemd の手動設定は不要です。インストーラーがすべて自動で行います。

### リポジトリを取得する

```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/sakusaku0214/vast-revenue-monitor.git
cd vast-revenue-monitor
```

### インストール前の確認（任意）

ファイルを変更せずに、リポジトリとホスト環境をチェックできます。

```bash
sudo bash install.sh --check
```

最後に次のメッセージが表示されれば成功です。

```text
[vast-revenue-monitor] Validation completed; no changes were made.
```

### インストールを実行する

```bash
sudo bash install.sh
```

対話形式で次の情報を入力します。

- Discord Webhook URL（画面に表示されず、2回入力）
- Vast.ai APIキー（画面に表示されず、2回入力）
- 週間収益目標（$）
- 詳細レポートを有効にするか（既定値：無効）
- 通知言語（Enterで英語）

```text
Select Discord notification language:
1) English
2) 日本語
Choice [1]:
```

インストール中に Vast.ai API、為替レート取得先、Discord Webhook の検証が行われます。検証に失敗した場合はインストールが中断され、不完全な状態はロールバックされます。

成功すると次のメッセージが表示されます。

```text
[vast-revenue-monitor] Installation completed successfully.
```

### 動作を確認する

```bash
sudo systemctl is-enabled vast-balance.service
sudo systemctl is-active vast-balance.service
sudo systemctl status vast-balance.service --no-pager
sudo journalctl -u vast-balance.service -n 50 --no-pager
```

`enabled` と `active` が表示されることを確認してください。

手動で1回だけ実行する場合：

```bash
sudo -u vast-revenue-monitor /opt/vast-revenue-monitor/.venv/bin/python /opt/vast-revenue-monitor/balance.py --config /opt/vast-revenue-monitor/config.json --once
```

バージョン確認：

```bash
sudo /opt/vast-revenue-monitor/.venv/bin/python /opt/vast-revenue-monitor/balance.py --version
```

### Vast.ai APIのレスポンス形式に関するエラー

`VastApiSchemaError` が出た場合、サービス自体は動作していますが、Vast.ai から返ってきた JSON に、このバージョンが期待する収益フィールドが含まれていません。

エラー発生時は、完全なレスポンスが権限を制限した状態で次の場所に保存されます。

```text
/opt/vast-revenue-monitor/logs/api_response.json
```

インストール中に失敗した場合は、次の場所に残ります。

```text
/tmp/vast-revenue-monitor-api_response.json
```

内容を確認する例：

```bash
sudo python3 -m json.tool /tmp/vast-revenue-monitor-api_response.json
sudo journalctl -u vast-balance.service -n 100 -l --no-pager
```

### 自動インストール（非対話モード）

環境変数で認証情報を渡してインストールできます。

```bash
export DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/.../...'
export VAST_API_KEY='your-vast-api-key'
export NOTIFICATION_LANGUAGE=ja   # 任意。en（デフォルト）または ja
sudo --preserve-env=DISCORD_WEBHOOK_URL,VAST_API_KEY,NOTIFICATION_LANGUAGE bash install.sh
unset DISCORD_WEBHOOK_URL VAST_API_KEY
```

`NOTIFICATION_LANGUAGE` を指定しない場合は英語になります。

## アップデート方法

対象のリリースを取得したうえで、インストールと同じコマンドを再実行します。

```bash
git pull origin main
sudo bash install.sh
```

既存の `config.json`、`state/`、`logs/`、履歴、記録、為替キャッシュは保持されます。活性化に失敗した場合は以前のバージョンにロールバックされます。

通常のアップグレードでは既存の `config.json` は上書きされず、言語選択画面も表示されません。

## 設定項目

設定ファイルの場所：`/opt/vast-revenue-monitor/config.json`

- `weekly_goal_usd`：週間目標（正の小数）
- `language`：`en` または `ja`

古い設定に `language` がない場合、または未対応の値が入っている場合は英語になります（警告後）。

### 再設定（週間目標・言語・詳細レポート）

```bash
sudo /opt/vast-revenue-monitor/reconfigure.sh
```

現在の週間目標、言語、詳細レポート設定を表示します。Enter で各設定を維持、`1` / `en` で英語、`2` / `ja` で日本語を選択できます。提案内容を確認してから書き込みます。`detailed_report` が導入される前に作成されたインストールでは、変更するまで「無効」が既定値になります。

API キー、Webhook、未知のキー、状態、履歴、記録は変更・表示しません。原子的に設定を書き込み、設定が実際に変更された場合のみ `vast-balance.service` を再起動します。言語を変更しても収益履歴はリセットされません。ゼロ、負数、不正な文字、NaN、無限値は拒否されます。

## 収益の計算方法

Vast.ai の current-user エンドポイントは週間の `balance` を提供します。時間・日・週・月の収益合計は直接提供されないため、本ツールは連続したバランスのサンプルを `state/` に保存し、正の差分だけを収益として集計します。

「直近区間」（英語表示では Hourly）は、最新の正常な観測で得た正の増加額そのものです。

## Discord通知の内容

日本語通知の例：

```text
💰 VAST.AI 毎時収益レポート
収益 — 直近区間 $5.36 · 本日 $20.00 · 今週 $95.00
週間目標 — 現在 $95.00 · 目標 $100.00 · 目標まで残り $5.00
Vast Revenue Monitor v1.1.0
```

## 保存されるデータ

- 設定：`/opt/vast-revenue-monitor/config.json`
- 状態・履歴：`state/`
- ログ：`logs/`

## サービス操作

```bash
sudo systemctl status vast-balance.service
sudo systemctl restart vast-balance.service
sudo journalctl -u vast-balance.service -f
```

## バックアップ・復元・アンインストール

```bash
sudo /opt/vast-revenue-monitor/install.sh --backup
sudo /opt/vast-revenue-monitor/install.sh --restore /path/to/vast-revenue-monitor-backup-YYYYMMDD-HHMMSS.tar.gz
sudo /opt/vast-revenue-monitor/uninstall.sh
```
バックアップにはAPIキー、Webhook、収益履歴が含まれます。
ファイル権限を `0600` に設定し、安全な場所へ保管してください。
必要に応じて、別途暗号化してください。

## トラブルシューティングとセキュリティ

ログの確認：

```bash
sudo journalctl -u vast-balance.service -n 100 -l
```

アプリケーションログ：

```text
/opt/vast-revenue-monitor/logs/vast-revenue-monitor.log
```

再起動に失敗した場合は `sudo systemctl restart vast-balance.service` を実行してください。

設定ファイルを公開しないでください。漏洩が疑われる場合は、Discord Webhook と Vast.ai API キーの両方をローテーションしてください。サービスは専用ユーザーで動作します。

## 免責事項

無保証で提供されます。Vast.ai の公式値と照合してください。会計、税務、投資・金融助言ではありません。
```

## 収益期間と確定期間の最高記録

すべての境界は設定タイムゾーン（既定値 `Asia/Tokyo`）を使用します。

* **本日**は 09:00 から翌日 08:59:59 までの進行中の営業日です。**昨日**はその直前に完了した 09:00〜09:00 の営業日で、本日の間は変化しません。
* **今週**は土曜 09:00 に始まります。ただし Vast.ai の支払リセットが遅れることがあるため、名目境界後に実際の残高減少を観測した時点でのみ週を確定します。09:00 を越えて残高が同額または増加している場合は通常の正の差分です。減少を確認すると直前の残高を完了週として保存し、残った残高で新しい週を開始します。
* **今月**は、実際のリセット確認時刻がそのローカル暦月に含まれる完了週の合計です。進行中の週は含みません。

直近区間（Hourly）は最新観測の正の差分で、直ちに最高記録を更新できます。日間・週間・月間 ATH と通知は、それぞれ完了営業日、残高減少で確定した完了週、完了暦月だけを使用します。サンプリング区間内の正確な獲得時刻が不明な収益は区間末の観測に帰属させ、補間・正規化しません。リセット後に残った残高も失わないよう確認観測に帰属させます。

### 遅延リセット破損の修復

修復は明示的に実行し、既定ではドライランです。通常処理と同じロックを取得し、根拠のある修正をすべて説明し、不明確な候補は変更しません。

```bash
sudo /opt/vast-revenue-monitor/.venv/bin/python /opt/vast-revenue-monitor/balance.py \
  --config /opt/vast-revenue-monitor/config.json --repair-state
sudo /opt/vast-revenue-monitor/.venv/bin/python /opt/vast-revenue-monitor/balance.py \
  --config /opt/vast-revenue-monitor/config.json --repair-state --apply
```

適用時は状態ディレクトリの隣に日時付き `repair-backup-*` を作成し、`config.json` と状態ツリー全体を保存してから原子的に書き込みます。バックアップには API キー、Discord Webhook、収益履歴が含まれるため、実運用設定と同様に保護してください。ロールバックはサービスを停止し、現在の設定・状態を退避して、バックアップの `config.json` と `state/` を所有者を維持して元の場所へ戻し、サービスを再起動します。

## 安全なアップグレード

推奨コマンドは Git チェックアウトを fast-forward のみで更新し、トランザクション対応インストーラーを実行します。

```bash
cd ~/vast-revenue-monitor
sudo ./update.sh
```

変更しない確認には `sudo ./update.sh --check` を使用します。更新処理は追跡ファイルの未コミット変更を既定で拒否し、同時実行を防ぎ、prune 付き fetch と旧・新コミット表示を行います。rebase、force-reset、ユーザーファイル・ブランチ・タグの削除は行いません。通常の `git pull` だけでは root 所有の `/opt` は更新されません。手動手順は次のとおりです。

```bash
git pull --ff-only origin main
sudo bash install.sh
```
