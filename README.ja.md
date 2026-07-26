# vast-revenue-monitor

<p>
  <img src="https://github.com/user-attachments/assets/4698af2b-3d8e-4d86-b5d8-8344717fcea3"
       alt="Vast Revenue Monitor Discord notification"
       width="465">
</p>

[English](README.md) | 日本語

**現在の安定版: v1.0.1**

**Vast.aiの収益を自動で監視し、Discordへ見やすい収益通知を送信するためのモニタリングサービスです。**

Python 3.12以降対応。Discordへの日英バイリンガル通知、収益履歴、最高記録、週間目標管理、為替換算などを備えた本番運用向けツールです

## 機能

- 直近区間（英語表示は Hourly）、本日、今週、今月の収益
- USDJPY の複数プロバイダーと永続キャッシュ
- 週間目標、最高記録、詳細レポート、GPU/API 警告
- 土曜日 09:00 JST のリセット、履歴・状態の原子的保存
- 英語 (`en`) / 日本語 (`ja`) の通知

「直近区間」は最新の正常な観測で得た正の増加額そのものです。60分移動合計でも、時間換算・補正したレートでもありません。短い手動区間や遅延区間も実額を表示します。

## 要件とインストール

Ubuntu 24.04 LTS、HTTPS 接続、`sudo`、Discord Webhook URL、Vast.ai API キーが必要です。

```bash
git clone https://github.com/sakusaku0214/vast-revenue-monitor.git
cd vast-revenue-monitor
sudo bash install.sh
```

初回対話設定では秘密情報を非表示で2回入力し、正の小数の週間収益目標を設定します。通知言語は次から選び、Enter は英語です。

```text
Select Discord notification language:
1) English
2) 日本語
Choice [1]:
```

非対話では必須の `DISCORD_WEBHOOK_URL`、`VAST_API_KEY` と任意の `NOTIFICATION_LANGUAGE`（`en` または `ja`、未設定時は `en`）を `sudo --preserve-env` で渡します。通常アップグレードで既存 `config.json` は上書きされず、言語選択も表示されません。

## 設定と運用

設定は `/opt/vast-revenue-monitor/config.json`、状態・履歴は `state/`、ログは `logs/` です。`weekly_goal_usd` は週間目標（正の小数）、`language` は `en` または `ja` です。古い設定に `language` がなければ英語、未対応値も警告後に英語となります。

```bash
sudo systemctl status vast-balance.service
sudo systemctl restart vast-balance.service
sudo journalctl -u vast-balance.service -f
sudo -u vast-revenue-monitor /opt/vast-revenue-monitor/.venv/bin/python /opt/vast-revenue-monitor/balance.py --config /opt/vast-revenue-monitor/config.json --once
sudo /opt/vast-revenue-monitor/.venv/bin/python /opt/vast-revenue-monitor/balance.py --version
```

## インストール後の再設定

```bash
sudo /opt/vast-revenue-monitor/reconfigure.sh
```

現在の週間目標と言語を表示し、Enter なら維持します。`1`/`en` は英語、`2`/`ja` は日本語です。提案内容を確認してから書き込みます。APIキー、Webhook、未知のキー、状態、履歴、記録は変更・表示せず、原子的に設定を書き、成功後だけ `vast-balance.service` を再起動します。言語変更で収益履歴はリセットされません。ゼロ、負数、不正文字、NaN、無限値は拒否されます。

## バックアップ、復元、削除、更新

```bash
sudo /opt/vast-revenue-monitor/install.sh --backup
sudo /opt/vast-revenue-monitor/install.sh --restore /path/to/vast-revenue-monitor-backup-YYYYMMDD-HHMMSS.tar.gz
sudo /opt/vast-revenue-monitor/uninstall.sh
```

バックアップには API キー、Webhook、収益履歴が含まれるため、`0600`、暗号化、安全な場所で保管し公開しないでください。旧バックアップの `language` 欠落にも対応します。更新は対象リリースを取得して `sudo bash install.sh` を再実行します。設定、状態、履歴、記録、為替キャッシュ、ログは維持されます。

## トラブルシューティングとセキュリティ

`sudo journalctl -u vast-balance.service -n 100 -l` と `/opt/vast-revenue-monitor/logs/vast-revenue-monitor.log` を確認してください。API スキーマ異常は権限制限された `logs/api_response.json` に保存されます。再起動失敗時は `sudo systemctl restart vast-balance.service` を実行します。設定を公開せず、漏えい時は両方の資格情報をローテーションしてください。サービスは専用ユーザーで動作します。

## 日本語通知例

```text
💰 VAST.AI 毎時収益レポート
収益 — 直近区間 $5.36 · 本日 $20.00 · 今週 $95.00
週間目標 — 現在 $95.00 · 目標 $100.00 · 目標まで残り $5.00
Vast Revenue Monitor v1.0.1
```

## 免責事項

無保証で提供されます。Vast.ai の公式値と照合してください。会計、税務、投資・金融助言ではありません。
