# Color Hunt

このプロジェクトの README は日本語と韓国語で提供されています。
이 프로젝트의 README는 일본어와 한국어로 제공됩니다.

- [日本語 (Japanese)](README.md)
- [한국어 (Korean)](README_ko.md)

---

QRコードで参加し、提示された色に似た物を周りで探して写真で提出するリアルタイムパーティーゲームです。
ホスト用のPC1台と参加者のスマートフォンさえあれば、同じWi-Fi(またはインターネット)上ですぐに進行できます。

## 目次

1. [スクリーンショット](#スクリーンショット)
2. [主な機能](#主な機能)
3. [チームメンバー](#チームメンバー)
4. [システム構成](#システム構成)
5. [技術スタック](#技術スタック)
6. [技術的課題と解決](#技術的課題と解決)
7. [実行方法](#実行方法)
8. [AWSデプロイ](#awsデプロイ)
9. [AIモデルについて](#aiモデルについて)
10. [プロジェクト構成](#プロジェクト構成)

---

## スクリーンショット

| イントロ | ニックネーム/アバター選択 | ゲーム進行 |
| :---: | :---: | :---: |
| <img src="docs/screenshots/01_intro.png" width="220"> | <img src="docs/screenshots/02_join.png" width="220"> | <img src="docs/screenshots/03_play.png" width="220"> |

| 最終結果 | ホスト画面 |
| :---: | :---: |
| <img src="docs/screenshots/04_results.png" width="220"> | <img src="docs/screenshots/05_host.png" width="220"> |

---

## 主な機能

- **QR参加**: ホストが `/host` でQRコードを表示すると、参加者はスキャンするだけで入場
- **遊び方イントロ**: 初回アクセス時に4ステップのスライドでルールを先に案内
- **アバター選択**: 動物の絵文字12種類から1つを選んでニックネームと共に入場、待機画面・ランキング・表彰台に表示され続ける
- **ランダム目標色**: 毎ラウンド完全にランダムなRGBカラーを提示(全3ラウンド)
- **AI写真採点**: 提出された写真から目標色に最も近い物体・領域を見つけ、色の類似度(80%) + 提出スピード(20%)でスコアを算出
- **リアルタイム同期**: 待機画面・進行状況・ランキングがポーリングで自動更新
- **ホスト操作**: ゲーム開始/次のラウンド/結果発表/リセット、そして**全員提出完了時にタイマーを待たずすぐに結果画面へ終了**する機能
- **韓国語 / 日本語** 全UI多言語対応
- **最終結果の紙吹雪演出**と表彰台(1〜3位)表示

---

## チームメンバー

| 役割 | 担当内容 |
| --- | --- |
| サーバー・ゲームロジック | Flaskアプリ構成、ゲーム状態管理(`game_state.py`)、参加者・管理者API、QR生成、写真分析パイプライン |
| 参加者画面・デザイン | 画面ルーティング(`routes/player.py`)、テンプレート、UI/UXデザイン全般、フロントJS |
| QA・運営 | 複数端末でのQRアクセステスト、ニックネーム重複・提出・タイマー・リセットのシナリオ検証、韓国語/日本語翻訳のチェック |

> GitHub: [Gapsick/findcolor](https://github.com/Gapsick/findcolor)

---

## システム構成

```
参加者のスマートフォン (Safari / Chrome)
        │  QRスキャン → HTTP(ポーリング)
        ▼
   Flaskサーバー (単一プロセス)
   ├─ ゲーム状態 (メモリ, GameRoom)
   ├─ 参加者/管理者ルート
   └─ 画像分析パイプライン
        ├─ YOLO11n-seg  (1次, 物体検出)
        ├─ LAB色領域検出 (2次, 背景フォールバック)
        └─ SlimSAM       (3次, GPU専用フォールバック)
        ▲
        │  ホストPC (同じサーバーに /host でアクセス)
   ホストのスマートフォンまたはPC
```

ゲーム状態はDBを使わずサーバープロセスのメモリで管理される構造のため、**Webプロセスは必ず1つだけ実行**する必要があります。

---

## 技術スタック

| 区分 | 使用技術 |
| --- | --- |
| バックエンド | Python, Flask |
| AI / 画像分析 | Ultralytics YOLO11n-seg, SlimSAM(Transformers), OpenCV, Pillow, PyTorch |
| フロントエンド | Jinja2テンプレート, Vanilla JS, CSS (カスタム, セルフホスティングWebフォント) |
| 認証・設定 | Flask Session, `python-dotenv`(.env) |
| デプロイ | AWS EC2(Ubuntu) + systemd, ローカルLANデプロイも併用可能 |

---

## 技術的課題と解決

### 課題: 20人が同時に写真を提出したら?

重いモデル1つで写真1枚を分析するのに約3秒かかるとすると、20人がほぼ同時に提出した場合、順次処理では `3秒 × 20人 = 60秒` かかります。リアルタイムパーティーゲームには適さない遅延でした。

### 解決

1. **軽量モデルの採用** — YOLOシリーズの中で最も軽い**YOLO11n(nano)**を使用。大きいモデルに比べてはるかに高速でありながら、一般的な物体認識には十分な精度
2. **GPU自動検出** — `torch.cuda.is_available()` でGPUの有無を検出し、自動でdeviceを選択。デプロイ環境を選ばない
3. **リクエストのバッチ処理** — 写真が届くたびに即座に処理するのではなく、**80ms以内に届いたリクエストを最大20枚までまとめて1回のバッチ推論**で処理。GPUは画像1枚と20枚をバッチ処理する時間差が大きくないため、`人数 × 処理時間`ではなく`バッチ1回`程度まで遅延が減ります。

さらに**段階的フォールバック構造**でリソースを節約します。

| 段階 | 方式 | コスト | 使用条件 |
| --- | --- | --- | --- |
| 1次 | YOLO11n-seg物体検出 | 低い | 常に試行 |
| 2次 | LAB色領域検出 | 非常に低い | YOLOが見つけられなかった時(芝生・壁などの背景) |
| 3次 | SlimSAM | 高い | それでも見つからず、**GPUがある時のみ** |

最も良いモデル1つだけを使う代わりに、状況と機材に合わせて段階的にツールを選択する構造で設計しました。

---

## 実行方法

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

`.env` ファイルを作成し、次の値を設定します(`.gitignore` に含まれているため git には上がりません):

```
COLORHUNT_SECRET=任意のランダム文字列
COLORHUNT_ADMIN_PIN=ホストPIN
```

```powershell
.venv\Scripts\python app.py
```

- 参加者: `http://<PCのIP>:5000/`
- ホスト: `http://<PCのIP>:5000/host`

同じWi-Fiではなくインターネット経由でデプロイする場合は、下記の[AWSデプロイ](#awsデプロイ)を参照してください。

---

## AWSデプロイ

学校や会社のWi-Fiのように端末間通信がブロックされていて同じWi-Fi経由でアクセスできない環境では、AWS EC2にデプロイしてインターネット経由でアクセスできるようにできます。必要なスクリプトは [`deploy/`](deploy/) フォルダにあらかじめ用意しています。

### 1. EC2インスタンスの作成

- OS: **Ubuntu 22.04以上のLTS**
- インスタンスタイプ: **t3.medium以上**を推奨(torch/ultralyticsがメモリを多く使うため、t2.micro/t3.microなどの無料利用枠のスペックでは不足する場合あり)
- キーペア: **新しいキーペアを作成**して `.pem` ファイルをダウンロード(ないと後でSSH接続できません)
- セキュリティグループ(ファイアウォール): インバウンドルールに **SSH(22)** と **カスタムTCP 5000**(ソース `0.0.0.0/0`)を追加
- ストレージ: **20〜30GB以上**を推奨(デフォルトの8GBだとPythonパッケージのインストールにはやや不足)

### 2. 接続してインストール

```bash
ssh -i "ダウンロードしたキー.pem" ubuntu@<EC2のパブリックIP>

git clone https://github.com/Gapsick/findcolor.git colorhunt
cd colorhunt
bash deploy/setup_ec2.sh
```

### 3. `.env` を転送

`.env` はgitに含まれていないため、自分のPCから直接コピーします。

```powershell
scp -i "ダウンロードしたキー.pem" .env ubuntu@<EC2のパブリックIP>:~/colorhunt/.env
```

### 4. systemdに登録して常時起動させる

```bash
sudo cp deploy/colorhunt.service /etc/systemd/system/colorhunt.service
# WorkingDirectoryが実際のclone先と違う場合はこのファイル内で修正
sudo systemctl daemon-reload
sudo systemctl enable --now colorhunt
sudo systemctl status colorhunt   # active (running) になっているか確認
```

### 5. 接続確認

- 参加者: `http://<EC2のパブリックIP>:5000`
- ホスト: `http://<EC2のパブリックIP>:5000/host`

> ⚠️ イベントが終わったらEC2インスタンスを**停止(Stop)** または **終了(Terminate)** してください。起動している時間分だけ料金が発生し続けます。

---

## AIモデルについて

基本分析にはリポジトリの `backend/yolo11n-seg.pt` を使用します。GPUがあれば自動的にCUDAを選択します。

YOLOが学習していない芝生・壁・床のような領域は、高速なLAB色領域検出で補い、連続する最も大きい類似色領域の輪郭を表示します。

サーバー起動時にモデルをウォームアップし、80ms以内に到着したリクエストを最大20枚まで自動的にまとめてバッチ推論します。

YOLOが物体を見つけられなかった場合、GPU環境でのみSlimSAMフォールバックを使用します。SlimSAMのチェックポイントは一度だけダウンロードすれば十分です。

```powershell
python -c "from transformers import SamModel, SamProcessor; SamProcessor.from_pretrained('Zigeng/SlimSAM-uniform-50'); SamModel.from_pretrained('Zigeng/SlimSAM-uniform-50')"
```

モデルはユーザーキャッシュに保存され、以降の実行では再ダウンロードされません。

---

## プロジェクト構成

```text
app.py                      実行エントリーポイント (.envロード、アプリ生成)
backend/
  game_state.py              参加者、タイマー、アバター、目標色、ラウンド状態
  i18n.py                    韓国語/日本語翻訳
  image_analysis.py          写真分析パイプライン (YOLO → LAB → SlimSAM)
  yolo_segmentation.py        YOLO11n-seg + リクエストバッチ処理
  sam_segmentation.py         SlimSAMフォールバック
  color_region_segmentation.py LAB色領域検出フォールバック
  qr_utils.py                 参加QR生成
  routes/
    player.py                 参加者画面ルート (イントロ/入場/待機/ゲーム/結果)
    admin.py                  ホストログイン・ダッシュボードルート
    api.py                    参加者・管理者API
    dev.py                     開発用プレビュールート (COLORHUNT_DEV=1の時のみ)
frontend/
  templates/                  Jinja2 HTMLテンプレート
  static/css/style.css         全体デザイン
  static/js/                   画面別動作スクリプト
  static/fonts/                セルフホスティングWebフォント
deploy/                      AWS EC2デプロイ用スクリプト・systemdサービスファイル
docs/screenshots/            README用スクリーンショット
```
