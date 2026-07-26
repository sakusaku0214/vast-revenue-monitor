# vast-revenue-monitor

[English](README.md) | 日本語

Vast.aiのアカウントbalanceを監視し、USD・JPYの毎時Discordレポートを送る
Python 3.12+向け常駐サービスです。

## 現在の安定版

**Current Stable Release: v1.0.0**

## 主な機能

- 直近の成功観測区間、09:00 JSTからの本日収益、現在の週間balanceを表示
- 英語・日本語のコンパクトDiscord通知と詳細通知
- 独立した週間目標、過去最高記録、記録更新通知
- 3系統のUSDJPY APIと永続キャッシュ
- atomicなJSON状態、年単位CSV履歴、30日圧縮ログ
- systemd、再設定、バックアップ・復元、完全アンインストール

## 必要環境

- Ubuntu 24.04 LTS、sudo権限、DNS・HTTPS接続
- Discord Webhook URL、Vast.ai APIキー

## インストール

```bash
sudo apt-get update && sudo apt-get install -y git
git clone <repository-url> vast-revenue-monitor
cd vast-revenue-monitor
sudo bash install.sh --check
sudo bash install.sh
```

初回設定ではWebhookとAPIキーを各2回、`weekly_goal_usd`、詳細通知、通知言語を
入力します。言語選択は`1) English`、`2) 日本語`で、Enterは英語です。

## 通知例

```text
💰 VAST.AI 毎時収益レポート

収益
直近区間 $5.36 / ¥878
本日 $16.07 / ¥2,632
今週 $139.97 / ¥22,928

週間目標
現在: $139.97
目標: $1,000.00
進捗: 14.0%
目標まで残り: $860.03

過去最高
直近区間: $11.61
日間: $82.21
週間: $139.97
月間: $98.28
```

## 収益計算

直近区間は最新の成功観測に対応する正のbalance差分だけです。60分換算、按分、
外挿はしません。比較元がなければ`$0.00`、減少・ゼロ変化も`$0.00`です。
Dailyは09:00 JST以降、Weeklyは現在のbalance、Monthlyは月初09:00以降です。
09:00をまたぐ差分は発生時刻を判断できないため、後側の観測日に全額計上します。

## サービス操作・手動実行・バージョン

```bash
sudo systemctl status vast-balance.service
sudo journalctl -u vast-balance.service -f
/opt/vast-revenue-monitor/.venv/bin/python /opt/vast-revenue-monitor/balance.py --version
sudo systemctl stop vast-balance.service
cd /opt/vast-revenue-monitor
sudo -u vast-revenue-monitor .venv/bin/python balance.py --config config.json --once
sudo systemctl start vast-balance.service
```

## 対話式再設定

```bash
sudo /opt/vast-revenue-monitor/reconfigure.sh
```

現在値を表示して週間目標と言語を変更します。Enterは現在値を維持します。
設定はatomicに保存され、APIキーとWebhookは表示・変更されず、成功後だけサービスを
再起動します。旧コマンド`sudo bash install.sh --reconfigure`も同じ処理を呼びます。

## バックアップ・復元

```bash
cd ~/vast-revenue-monitor
sudo bash install.sh --backup
sudo bash install.sh --restore /path/to/vast-revenue-monitor-backup-YYYYMMDD-HHMMSS.tar.gz
```

バックアップには`config.json`と`state/`（履歴、記録、収益イベント）が含まれます。
APIキーとDiscord Webhookを含む機密ファイルなので、公開・Git登録せず安全に保管して
ください。復元時はパス、リンク、種類、件数、展開サイズ、設定値を検証します。

## 完全アンインストール

```bash
cd ~/vast-revenue-monitor
sudo bash uninstall.sh
```

`Y`は完全削除、`N`は安全なバックアップを作成・検証してから完全削除します。

## 設定・パス

- 設定: `/opt/vast-revenue-monitor/config.json`
- 状態・履歴: `/opt/vast-revenue-monitor/state/`
- ログ: `/opt/vast-revenue-monitor/logs/vast-revenue-monitor.log`
- 主なキー: `weekly_goal_usd`、`language` (`en`/`ja`)、`detailed_report`

古い設定に`language`がなければ英語です。通常インストール・復元では既存の認証情報、
目標、未知の設定キー、stateを保持します。

## トラブルシューティングとセキュリティ

```bash
sudo journalctl -u vast-balance.service -n 100 -l --no-pager
sudo systemctl restart vast-balance.service
```

専用非ログインユーザー、systemd sandbox、制限権限、秘密情報マスクを使用します。
Webhook、APIキー、バックアップ、診断JSONを第三者へ共有しないでください。

## アップグレード

```bash
cd ~/vast-revenue-monitor
sudo bash install.sh --backup
git pull
git log -1 --oneline
sudo bash install.sh --check
sudo bash install.sh
```

## 免責事項

本ツールはVast.aiの非公式監視ツールです。収益は観測したVast.aiアカウントbalanceの
変化から推定され、最終的な精算・請求・税務記録と一致しない場合があります。
Vast.aiとの提携関係はなく、Vast.aiによる承認・保証を受けたものではありません。
