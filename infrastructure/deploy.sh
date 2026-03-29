#!/bin/bash
set -e

DB_HOST=$1
REPO=$2

cd /home/ec2-user
mkdir -p flow-app
cd flow-app

echo "1. Downloading docker-compose.prod.yml..."
curl -s -O "https://raw.githubusercontent.com/$REPO/main/docker-compose.prod.yml"

echo "2. Fetching secrets from AWS SSM..."
DB_PASS=$(aws ssm get-parameter --name "/prod/db/password" --with-decryption --query "Parameter.Value" --output text --region eu-north-1)

aws ssm get-parameter --name "/prod/jwt/private" --with-decryption --query "Parameter.Value" --output text --region eu-north-1 > secrets/prod/jwt-private.pem
aws ssm get-parameter --name "/prod/jwt/public" --with-decryption --query "Parameter.Value" --output text --region eu-north-1 > secrets/prod/jwt-public.pem
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
EOF

echo "4. Pulling new Docker image..."
docker compose -f docker-compose.prod.yml pull

echo "5. Running Alembic migrations..."
docker compose -f docker-compose.prod.yml run --rm app alembic upgrade head

echo "6. Restarting application..."
docker compose -f docker-compose.prod.yml up -d

echo "Deployment successful! 🚀"