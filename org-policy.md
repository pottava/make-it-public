## 組織ポリシーの緩和

このハンズオンは厳しい組織ポリシー下においては実施が困難です。  
以下の通り、いくつか組織ポリシーの緩和を行ってください。

## 適用対象

この手順は全て特定のプロジェクトの組織ポリシーを上書きする例になっています。環境変数を設定しましょう。

```bash
export GOOGLE_CLOUD_PROJECT=$( gcloud config get-value project )
```

組織全体に対してポリシーを変更する場合は以下のコマンドを実行し

```bash
export ORGANIZATION_ID=$( gcloud organizations list --format 'value(ID)' )
echo "Organization ID: ${ORGANIZATION_ID}"
```

この先のコマンドの `--project "${GOOGLE_CLOUD_PROJECT}"` をすべて `--organization ${ORGANIZATION_ID}"` に置換して実行してください。

## サービスアカウントとその鍵

作成を制限するポリシーを緩和してください。

```bash
gcloud resource-manager org-policies disable-enforce iam.disableServiceAccountCreation \
    --project "${GOOGLE_CLOUD_PROJECT}"
gcloud resource-manager org-policies disable-enforce iam.disableServiceAccountKeyCreation \
    --project "${GOOGLE_CLOUD_PROJECT}"
```

状況を確認します。

```bash
gcloud resource-manager org-policies describe iam.disableServiceAccountCreation \
    --project "${GOOGLE_CLOUD_PROJECT}" --effective
gcloud resource-manager org-policies describe iam.disableServiceAccountKeyCreation \
    --project "${GOOGLE_CLOUD_PROJECT}" --effective
```

## インターネット ネットワーク エンドポイント グループ

作成を制限するポリシーを緩和してください。

```bash
gcloud resource-manager org-policies disable-enforce compute.disableInternetNetworkEndpointGroup \
    --project "${GOOGLE_CLOUD_PROJECT}"
```

状況を確認します。

```bash
gcloud resource-manager org-policies describe compute.disableInternetNetworkEndpointGroup \
    --project "${GOOGLE_CLOUD_PROJECT}" --effective
```
