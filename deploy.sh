#!/bin/bash
# Quick deployment script for testing

echo "Vaultwarden Backup - Quick Deploy"
echo "=================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env with your actual credentials before continuing!"
    echo ""
    read -p "Press Enter after editing .env to continue..."
fi

# Build and start
echo "Building Docker image..."
docker-compose build

echo ""
echo "Starting container..."
docker-compose up -d

echo ""
echo "✅ Container started!"
echo ""
echo "View logs with: docker-compose logs -f"
echo "Stop with: docker-compose down"
echo ""
