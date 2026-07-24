#!/bin/bash
set -e
echo "Начало деплоя"

git pull

docker compose build
docker compose run --rm frontend
docker compose run --rm static
docker compose up -d db backend

systemctl reload nginx

echo "Отправляется уведомление о деплое в rollbar"
COMMIT_HASH=$(git rev-parse HEAD)
source ../.env

curl --request POST \
     --url https://api.rollbar.com/api/1/deploy \
     --header "X-Rollbar-Access-Token: $ROLLBAR_TOKEN" \
     --header 'accept: application/json' \
     --header 'content-type: application/json' \
     --data '{
  "environment": "production",
  "status": "succeeded",
  "revision": "'"$COMMIT_HASH"'"
}'

echo "Уведомление в rollbar отправлено"

echo "Успешно"
