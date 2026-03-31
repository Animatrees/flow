#!/bin/bash
set -euo pipefail

AWS_REGION=${AWS_REGION:-eu-north-1}
DB_HOST=$1
ARTIFACTS_BUCKET=$2
RELEASE_REF=$3
S3_BUCKET=$4
APP_DIR=/home/ec2-user/flow-app
TMP_DIR=$(mktemp -d)
BUNDLE_URI="s3://${ARTIFACTS_BUCKET}/${RELEASE_REF}/bundle.tar.gz"

cleanup() {
  rm -rf "$TMP_DIR"
}

trap cleanup EXIT

mkdir -p "$APP_DIR"
cd "$APP_DIR"

echo "1. Downloading deployment bundle from ${BUNDLE_URI}..."
aws s3 cp "$BUNDLE_URI" "${TMP_DIR}/bundle.tar.gz" --region "$AWS_REGION"
tar -xzf "${TMP_DIR}/bundle.tar.gz" -C "$TMP_DIR"

install -m 644 "${TMP_DIR}/docker-compose.prod.yml" "${APP_DIR}/docker-compose.prod.yml"
install -m 600 "${TMP_DIR}/release.env" "${APP_DIR}/release.env"

set -a
# shellcheck disable=SC1091
source "${APP_DIR}/release.env"
set +a

: "${APP_IMAGE:?APP_IMAGE is required}"
: "${RELEASE_VERSION:?RELEASE_VERSION is required}"

echo "2. Fetching secrets from AWS SSM..."
mkdir -p secrets/prod
DB_PASS=$(aws ssm get-parameter --name "/prod/db/password" --with-decryption --query "Parameter.Value" --output text --region "$AWS_REGION")

aws ssm get-parameter --name "/prod/jwt/private" --with-decryption --query "Parameter.Value" --output text --region "$AWS_REGION" > secrets/prod/jwt-private.pem
aws ssm get-parameter --name "/prod/jwt/public" --with-decryption --query "Parameter.Value" --output text --region "$AWS_REGION" > secrets/prod/jwt-public.pem
chmod 600 secrets/prod/jwt-private.pem

echo "3. Generating .env.prod..."
cat <<EOF > .env.prod
DB__NAME=flow
DB__USER=flow
DB__PASSWORD=$DB_PASS
DB__PORT=5432
DB__HOST=$DB_HOST
RUN__HOST=0.0.0.0
RUN__PORT=8000
JWT__PRIVATE_KEY_PATH=/run/secrets/flow/jwt-private.pem
JWT__PUBLIC_KEY_PATH=/run/secrets/flow/jwt-public.pem
S3__BUCKET=$S3_BUCKET
S3__REGION=$AWS_REGION
S3__PRESIGN_EXPIRE_SECONDS=900
EOF

echo "4. Pulling image ${APP_IMAGE}..."
docker compose -f docker-compose.prod.yml pull

echo "5. Running Alembic migrations..."
docker compose -f docker-compose.prod.yml run --rm app alembic upgrade head

echo "6. Restarting application..."
docker compose -f docker-compose.prod.yml up -d --remove-orphans

echo "7. Waiting for health check..."
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1/api/v1/health-check/ > /dev/null; then
    echo "Deployment successful for ${RELEASE_VERSION}"
    exit 0
  fi

  sleep 5
done

echo "Health check did not pass in time" >&2
docker compose -f docker-compose.prod.yml ps >&2
exit 1
