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
export PROJECT_NUMBER=$( gcloud projects describe ${GOOGLE_CLOUD_PROJECT} --format='value(projectNumber)' )
```

[Vertex AI](https://cloud.google.com/vertex-ai?hl=ja) など、関連サービスを有効化し、利用できる状態にします。

```bash
gcloud services enable compute.googleapis.com storage.googleapis.com networksecurity.googleapis.com certificatemanager.googleapis.com logging.googleapis.com monitoring.googleapis.com iap.googleapis.com iamcredentials.googleapis.com aiplatform.googleapis.com cloudresourcemanager.googleapis.com
```

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
gcloud compute firewall-rules create allow-from-internal --network "demo" --direction "INGRESS" --priority 1000 --action "ALLOW" --rules "all" --source-ranges "192.168.0.0/24"
```

クラウドのコンソールから設定情報を確認してみましょう。  
https://console.cloud.google.com/networking/networks/list

## 3. GCS バケットに静的コンテンツをアップロードする

個人やチームの名前など、一意に特定できるアルファベットを `YOUR_ID` として環境変数に設定します。

```bash
export YOUR_ID=
```

バケットを作ります。

```bash
gcloud storage buckets create "gs://demo-202504-${YOUR_ID}" --location "asia-northeast1" --default-storage-class "STANDARD" --uniform-bucket-level-access
```

index.html と style.css をアップロードしてみましょう。

```bash
echo '<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>サンプル</title><link rel="stylesheet" href="style.css"></head><body><h1>Hello <span class="blue">G</span><span class="red">o</span><span class="yellow">o</span><span class="blue">g</span><span class="green">l</span><span class="red">e</span>!</h1></body></html>' > index.html
gcloud storage cp index.html "gs://demo-202504-${YOUR_ID}"
echo '.blue { color: #4285F4; } .red { color: #EA4335; } .yellow { color: #FBBC05; } .green  { color: #34A853; }' > style.css
gcloud storage cp style.css "gs://demo-202504-${YOUR_ID}"
```

GCS アクセス用サービスアカウントを作り

```bash
gcloud iam service-accounts create "hmac-for-demo-${YOUR_ID}" --display-name "Service Account for GCS CDN Access"
gcloud storage buckets add-iam-policy-binding gs://demo-202504-${YOUR_ID} --member "serviceAccount:hmac-for-demo-${YOUR_ID}@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com" --role "roles/storage.objectViewer"
```

そのサービスアカウントで GCS バケットに HMAC キーを作成します。

```bash
gcloud storage hmac create "hmac-for-demo-${YOUR_ID}@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"
```

画面に表示された値を環境変数に保存してください。

```bash
export HMAC_ACCESS_KEY="<表示された accessId>"
export HMAC_SECRET="<表示された secret>"
```

クラウドのコンソールから Cloud Storage の中身を確認してみましょう。  
https://console.cloud.google.com/storage/browser

## 4. ロードバランサーの作成

ロードバランサーに割り当てる静的外部 IP アドレスを予約します。

```bash
gcloud compute addresses create "${YOUR_ID}-lb-ip" --global
```

あなたの現在の接続元 IP アドレスを確認してみましょう。  
https://api.myip.com/

それを考慮しつつ、接続を許可する IP アドレスを指定してください。

```bash
export ALLOWED_IP_RANGE="$( curl -4 ifconfig.me )/32"
```

Cloud Armor のセキュリティ ポリシーを作成します。

```bash
gcloud compute security-policies create "${YOUR_ID}-armor-policy" --description="Allow only specific IPs"
gcloud compute security-policies rules create 10000 --security-policy "${YOUR_ID}-armor-policy" --description "Allow traffic from trusted sources" --action "allow" --src-ip-ranges "${ALLOWED_IP_RANGE}"
gcloud compute security-policies rules update 2147483647 --security-policy "${YOUR_ID}-armor-policy" --description="Default deny all other traffic" --action "deny-403"
```

GCS に向けたバックエンドサービスを作り、

```bash
gcloud compute network-endpoint-groups create "gcs-neg" --network-endpoint-type "internet-fqdn-port" --global
gcloud compute network-endpoint-groups update "gcs-neg" --add-endpoint "fqdn=demo-202504-${YOUR_ID}.storage.googleapis.com,port=443" --global
gcloud compute backend-services create "gcs-backend" --load-balancing-scheme "EXTERNAL_MANAGED" --protocol HTTPS --enable-cdn --cache-mode "USE_ORIGIN_HEADERS" --global
gcloud compute backend-services add-backend "gcs-backend" --network-endpoint-group "gcs-neg" --global-network-endpoint-group --global
gcloud compute backend-services export "gcs-backend" --destination "gcs-backend-service.yaml" --global
echo "customRequestHeaders:" >> gcs-backend-service.yaml
echo "- host:demo-202504-${YOUR_ID}.storage.googleapis.com" >> gcs-backend-service.yaml
echo "securitySettings:" >> gcs-backend-service.yaml
echo "  awsV4Authentication:" >> gcs-backend-service.yaml
echo "    accessKeyId: ${HMAC_ACCESS_KEY}" >> gcs-backend-service.yaml
echo "    accessKey: ${HMAC_SECRET}" >> gcs-backend-service.yaml
echo "    originRegion: asia-northeast1" >> gcs-backend-service.yaml
gcloud compute backend-services import "gcs-backend" --source "gcs-backend-service.yaml" --global
gcloud compute backend-services update "gcs-backend" --security-policy "${YOUR_ID}-armor-policy" --global
```

続けて URL マップ・ターゲット プロキシ・グローバル転送ルールを作成します。

```bash
gcloud compute url-maps create "demo-${YOUR_ID}-urlmap" --default-service "gcs-backend"
gcloud compute target-http-proxies create "http-proxy" --url-map "demo-${YOUR_ID}-urlmap"
gcloud compute forwarding-rules create "http-forward" --load-balancing-scheme "EXTERNAL_MANAGED" --address "${YOUR_ID}-lb-ip" --target-http-proxy "http-proxy" --ports 80 --global
```

クラウドのコンソールからロードバランサーや WAF の設定を確認してみましょう。

- https://console.cloud.google.com/net-services/loadbalancing/list/loadBalancers
- https://console.cloud.google.com/net-security/securitypolicies/list

では

```bash
echo "http://$( gcloud compute addresses describe "${YOUR_ID}-lb-ip" --global --format='value(address)' )/"
```

## これで終わりです

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>

お疲れさまでした！
