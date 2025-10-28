#!/usr/bin/env bash
set -euo pipefail
echo "Building and starting cluster..."
docker compose -f docker/docker-compose.yml up --build -d
echo "Waiting 5s for services to start..."
sleep 5
echo "Health check:"
for p in 8001 8002 8003; do
  echo -n "http://localhost:${p}/health -> "
  curl -sS "http://localhost:${p}/health" || echo "no response"
done
