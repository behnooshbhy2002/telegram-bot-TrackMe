#!/bin/bash

# Telegram Task Bot Deployment Script

echo "🚀 Starting Telegram Task Bot deployment..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please create .env file with your configuration."
    echo "Example:"
    echo "BOT_TOKEN=your_bot_token_here"
    echo "USER1_ID=123456789"
    echo "USER1_NAME=User1"
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data logs

# Set proper permissions
chmod 755 data logs

# Stop existing container if running
echo "🛑 Stopping existing container..."
docker-compose down

# Build and start the container
echo "🔨 Building and starting container..."
docker-compose up -d --build

# Show container status
echo "📊 Container status:"
docker-compose ps

# Show logs
echo "📋 Recent logs:"
docker-compose logs --tail=20

echo "✅ Deployment completed!"
echo ""
echo "🔧 Useful commands:"
echo "View logs: docker-compose logs -f"
echo "Stop bot: docker-compose down"
echo "Restart bot: docker-compose restart"
echo "Update bot: docker-compose down && docker-compose up -d --build"