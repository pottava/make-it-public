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

この `demo` というグローバル ネットワークに対し、[Identity-Aware Proxy](https://cloud.google.com/iap?hl=ja)、内部ネットワーク、またはロードバランサーからの接続を許可します。

```bash
gcloud compute firewall-rules create allow-from-iap --network "demo" --direction "INGRESS" --priority 1000 --action "ALLOW" --rules "tcp:22,icmp" --source-ranges "35.235.240.0/20"
gcloud compute firewall-rules create allow-from-internal --network "demo" --direction "INGRESS" --priority 1000 --action "ALLOW" --rules "all" --source-ranges "192.168.0.0/24"
gcloud compute firewall-rules create allow-health-checks --network "demo" --direction "INGRESS" --priority 1000 --action "ALLOW" --rules "tcp:80,tcp:443" --source-ranges "130.211.0.0/22,35.191.0.0/16" --target-tags "http-server"
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

最後に接続確認です。以下で返ってくる URL にアクセスしてみましょう。
ロードバランサーや IP アドレス制限がもれなく反映されるまで 10 分程度かかる可能性もあります。気長にお待ちください。

```bash
echo "http://$( gcloud compute addresses describe "${YOUR_ID}-lb-ip" --global --format='value(address)' )/index.html"
```

## 5. Web サーバーの起動

起動したいサーバーの条件をテンプレートとして登録します。

```bash
gcloud compute instance-templates create "demo-server" --machine-type "n2-standard-2" --image-family "debian-11" --image-project "debian-cloud" --tags "http-server" --metadata-from-file "startup-script=startup.sh"
```

マネージド インスタンスグループ (MIG) というサーバーの集合（といいつつ 1 台のみ）を作成します。

```bash
gcloud compute instance-groups managed create "demo-servers" --template "demo-server" --base-instance-name "demo-server" --size 1 --zone "asia-northeast1-b"
```

OS Login でサーバーの中に入ってみましょう。Y/n を聞かれたら Y、その後ローカルで鍵を作成する確認があったら Enter を 2 度押してください。

```bash
export demo_server_name=$( gcloud compute instances list --filter="name~'^demo-server'" --format="value(name)" )
gcloud compute ssh "${demo_server_name}" --zone "asia-northeast1-b"
```

サーバーに入ったら Flask（Python 製 Web サーバー）が起動していることを確認したら、Python を書き換えられるようサーバー上の権限設定を変更し、ログアウトしましょう。

```bash
curl -i http://localhost/api/gemini
sudo chown -R $USER /apps
logout
```

ローカルで app.py を編集し、それを Web サーバーに送信、応答が変化することを確かめてみましょう。

```bash
gcloud compute scp main.py "${demo_server_name}:/apps/main.py" --zone "asia-northeast1-b"
gcloud compute ssh "${demo_server_name}" --zone "asia-northeast1-b" -- curl -i http://localhost/api/gemini
```

## 6. ロードバランサーの設定変更

Web サーバーが正しく起動していることを確認する "ヘルスチェック" とロードバランサーのバックエンド サービスを設定します。

```bash
gcloud compute health-checks create http "vm-http-health-check" --port 80 --global
gcloud compute backend-services create "vm-backend" --load-balancing-scheme "EXTERNAL_MANAGED" --protocol HTTP --port-name "http" --health-checks "vm-http-health-check" --global
gcloud compute backend-services add-backend "vm-backend" --instance-group "demo-servers" --instance-group-zone "asia-northeast1-b" --global
gcloud compute backend-services update "vm-backend" --security-policy "${YOUR_ID}-armor-policy" --global
```

URL が /api/ で始まる場合は Web サーバーへルーティングするようロードバランサーの設定を変更します。

```bash
gcloud compute url-maps add-path-matcher "demo-${YOUR_ID}-urlmap" --default-service "gcs-backend" --path-matcher-name "web-path-matcher" --path-rules "^/api/.*=vm-backend"
```

最後に、Gemini の実装をするであろう API 以下にアクセスしてみましょう！

```bash
echo "http://$( gcloud compute addresses describe "${YOUR_ID}-lb-ip" --global --format='value(address)' )/api/gemini"
```

## これで終わりです

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>

お疲れさまでした！
