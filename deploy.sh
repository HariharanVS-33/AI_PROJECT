#!/bin/bash
# Simple deployment script for VPS

echo "🚀 Starting deployment..."

# Ensure we have a .env file
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found. Please create one based on README.md."
    exit 1
fi

# Ensure data directory exists
mkdir -p data/chromadb

# Build and start the container in detached mode
echo "🐳 Building and starting Docker container..."
docker-compose up -d --build

echo "✅ Deployment complete! The app should be running on port 8000."
echo "You can check logs with: docker-compose logs -f"
