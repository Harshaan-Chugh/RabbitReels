#!/bin/bash
# Development startup script

echo "🚀 Starting RabbitReels Development Environment..."

# Start infrastructure
echo "📦 Starting Redis & RabbitMQ..."
docker compose up -d rabbitmq redis

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Start API in background
echo "🔧 Starting FastAPI backend..."
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8080 &
API_PID=$!
cd ..

# Start Next.js frontend
echo "🌐 Starting Next.js frontend..."
cd web
npm run dev &
WEB_PID=$!
cd ..

echo "✅ Development environment started!"
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 API: http://localhost:8080"
echo "🐰 RabbitMQ Management: http://localhost:15672"
echo "📊 Redis: localhost:6379"
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for interrupt
trap 'echo "🛑 Stopping services..."; kill $API_PID $WEB_PID; docker compose down; exit' INT
wait
