#!/bin/bash

set -euo pipefail

ENV_FILE=".env"

# 若有舊的 .env，就先載入當作預設值
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

# 定義一個函式來詢問變數
ask() {
  local name="$1"
  local current="${!name-}"  # 取目前環境的值（若有）
  local prompt

  if [[ -n "${current:-}" ]]; then
    prompt="Enter $name (default: $current): "
  else
    prompt="Enter $name: "
  fi

  read -r -p "$prompt" input

  # 空輸入就沿用舊值；否則更新
  if [[ -z "${input:-}" && -n "${current:-}" ]]; then
    export "$name=$current"
  else
    export "$name=$input"
  fi
}

echo "Generating .env file..."
echo "=== Fill in variables to generate ENV_FILE ==="
# 清空並重新創建 .env 檔案
> "$ENV_FILE"
# 不需要使用者輸入的所有變數
INTERNAL_SHARED_SECRET="$(openssl rand 512 | base64)"
export INTERNAL_SHARED_SECRET
printf 'INTERNAL_SHARED_SECRET=%q\n' "$INTERNAL_SHARED_SECRET" >> "$ENV_FILE"
# 需要使用者輸入的所有變數（順序決定互動順序）
VARS=(
  OAUTH2_CLIENT_ID
  OAUTH2_CLIENT_SECRET
  GCP_BQ_PROJECT_ID
  GCP_SA_INPUT_PATH
  AWS_ACCESS_KEY
  AWS_SECRET_KEY
  AWS_REGION
  ICEBERG_S3_URL
  EXCHANGE_S3_URLS
)
for v in "${VARS[@]}"; do
  ask "$v"
  val="${!v-}"
  printf '%s=%q\n' "$v" "$val" >> "$ENV_FILE"
done
echo "$ENV_FILE generated successfully."

# 檢查 envsubst command 是否存在
if ! command -v envsubst >/dev/null 2>&1; then
  echo "Error: envsubst not found. Please install gettext." >&2
  exit 1
fi

echo "Generating values.yaml from values-template.yaml..."
envsubst < "values-template.yaml" > "values.yaml"
echo "values.yaml generated successfully."
