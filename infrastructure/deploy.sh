#!/bin/bash
set -e

AWS_REGION=${AWS_REGION:-eu-north-1}
DB_HOST=$1
REPO=$2
S3_BUCKET=$3

cd /home/ec2-user
mkdir -p flow-app
cd flow-app

echo "1. Downloading docker-compose.prod.yml..."
curl -s -O "https://raw.githubusercontent.com/$REPO/main/docker-compose.prod.yml"

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

echo "4. Pulling new Docker image..."
docker compose -f docker-compose.prod.yml pull

echo "5. Running Alembic migrations..."
docker compose -f docker-compose.prod.yml run --rm app alembic upgrade head

echo "6. Restarting application..."
docker compose -f docker-compose.prod.yml up -d

echo "Deployment successful! 🚀"
