# Google Cloud でのサイト公開ハンズオン

## 始めましょう

この手順ではクラウド上に Web サイトを設置するまでの流れを確認します。

<walkthrough-tutorial-duration duration="30"></walkthrough-tutorial-duration>
<walkthrough-tutorial-difficulty difficulty="1"></walkthrough-tutorial-difficulty>

**前提条件**:

- Google Cloud 上にプロジェクトが作成してある
- プロジェクトの _編集者_ 相当の権限をもつユーザーでログインしている
- _プロジェクト IAM 管理者_ 相当の権限をもつユーザーでログインしている
- もしくはプロジェクトの _オーナー_ 相当の権限をもつユーザーでログインしている
- (推奨) Google Chrome を利用している

**[開始]** ボタンをクリックして次のステップに進みます。

## プロジェクトの設定

この手順の中で実際にリソースを構築する対象のプロジェクトを選択してください。

<walkthrough-project-setup></walkthrough-project-setup>

## 1. CLI の初期設定 & API の有効化

[gcloud（Google Cloud の CLI ツール)](https://cloud.google.com/sdk/gcloud?hl=ja) のデフォルト プロジェクトを設定します。

```bash
export GOOGLE_CLOUD_PROJECT=<walkthrough-project-id/>
```

```bash
gcloud config set project "${GOOGLE_CLOUD_PROJECT}"
```

[Vertex AI](https://cloud.google.com/vertex-ai?hl=ja) など、関連サービスを有効化し、利用できる状態にします。

<walkthrough-enable-apis apis=
  "compute.googleapis.com,
  aiplatform.googleapis.com,
  run.googleapis.com,
  logging.googleapis.com,
  iap.googleapis.com,
  iamcredentials.googleapis.com,
  cloudresourcemanager.googleapis.com">
</walkthrough-enable-apis>

## 2. ネットワーク

`demo` という名前のグローバル ネットワークを作成し

```bash
gcloud compute networks create "demo" --subnet-mode "custom"
```

その中の東京リージョンに、254 個のプライベート IP アドレスが利用できる小規模ネットワークを `demo-tokyo` という名前で構成してみます。

```bash
gcloud compute networks subnets create "demo-tokyo" --network "demo" --region "asia-northeast1" --range "192.168.0.0/24" --enable-private-ip-google-access
```

この `demo` というグローバル ネットワークに対し、[Identity-Aware Proxy](https://cloud.google.com/iap?hl=ja)、または内部ネットワークからの接続を許可します。

```bash
gcloud compute firewall-rules create allow-from-iap --network "demo" --direction "INGRESS" --priority 1000 --action "ALLOW" --rules "tcp:22,icmp" --source-ranges "35.235.240.0/20"
gcloud compute firewall-rules create allow-from-internal --network "demo" --direction "INGRESS" --priority 1000 --action "ALLOW" --rules "tcp:0-65535,udp:0-65535,icmp" --source-ranges "192.168.0.0/24"
```

クラウドのコンソールから設定情報を確認してみましょう。  
https://console.cloud.google.com/networking/networks/list

## 3. GCS バケットに静的コンテンツをアップロードする

個人やチームの名前など、一意に特定できるアルファベットを `YOUR_ID` として環境変数に設定します。

```bash
export YOUR_ID=
```

バケットを作り、インデックス ページとして `index.html` を指定しておきます。

```bash
gcloud storage buckets create "gs://hackathon-2025-demo-${YOUR_ID}" --location "asia-northeast1" --default-storage-class "STANDARD" --uniform-bucket-level-access
gcloud storage buckets update "gs://hackathon-2025-demo-${YOUR_ID}" --web-main-page-suffix "index.html"
```

index.html と index.css をアップロードしてみましょう。

```bash
echo '<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>サンプル</title><link rel="stylesheet" href="style.css"></head><body><h1>Hello <span class="blue">G</span><span class="red">o</span><span class="yellow">o</span><span class="blue">g</span><span class="green">l</span><span class="red">e</span>!</h1></body></html>' > index.html
gcloud storage cp index.html "gs://hackathon-2025-demo-${YOUR_ID}"
echo '.blue { color: #4285F4; } .red { color: #EA4335; } .yellow { color: #FBBC05; } .green  { color: #34A853; }' > index.css
gcloud storage cp index.css "gs://hackathon-2025-demo-${YOUR_ID}"
```

クラウドのコンソールから Cloud Storage の中身を確認してみましょう。  
https://console.cloud.google.com/storage/browser

## これで終わりです

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>

お疲れさまでした！
