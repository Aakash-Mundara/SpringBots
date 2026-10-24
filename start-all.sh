#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$ROOT/local/logs" "$ROOT/local/seaweed" "$ROOT/local/files"
find_bin() { if [[ -x "$ROOT/local/bin/$1" ]]; then echo "$ROOT/local/bin/$1"; else command -v "$1" || true; fi; }
WEED="$(find_bin weed)"; ELASTIC="$ROOT/local/bin/elasticmq-server-all.jar"
if [[ -z "$WEED" ]]; then echo "Missing weed binary. Put it in ./local/bin/weed or add it to PATH."; exit 1; fi
if [[ ! -f "$ELASTIC" ]]; then echo "Missing ElasticMQ jar: place standalone jar at ./local/bin/elasticmq-server-all.jar"; exit 1; fi
if ! command -v java >/dev/null 2>&1; then echo "Java 21+ is required."; exit 1; fi
if ! command -v npm >/dev/null 2>&1; then echo "Node 20+ and npm are required."; exit 1; fi
if ! (echo >/dev/tcp/127.0.0.1/5432) >/dev/null 2>&1; then echo "PostgreSQL must be running on localhost:5432 first."; exit 1; fi
(cd "$ROOT" && "$WEED" server -dir="$ROOT/local/seaweed" -s3 > "$ROOT/local/logs/seaweed.log" 2>&1 & echo $! > "$ROOT/local/logs/seaweed.pid")
(cd "$ROOT" && java -Dconfig.file="$ROOT/local/elasticmq.conf" -jar "$ELASTIC" > "$ROOT/local/logs/elasticmq.log" 2>&1 & echo $! > "$ROOT/local/logs/elasticmq.pid")
sleep 3
(cd "$ROOT" && ./mvnw -q -DskipTests spring-boot:run > "$ROOT/local/logs/backend.log" 2>&1 & echo $! > "$ROOT/local/logs/backend.pid")
(cd "$ROOT/frontend" && if [[ ! -d node_modules ]]; then npm install; fi && npm run dev > "$ROOT/local/logs/frontend.log" 2>&1 & echo $! > "$ROOT/local/logs/frontend.pid")
echo "OnboardIQ services starting. Frontend: http://localhost:5173 | API: http://localhost:8080/api/v1/health | Swagger: http://localhost:8080/swagger-ui.html | ElasticMQ stats: http://localhost:9325"
echo "Logs: $ROOT/local/logs"
