#!/bin/bash
# ExpiredDomain.dev - EasyPanel Deployment Setup Script
# Bu script ilk kurulum için gerekli adımları otomatikleştirir

echo "🚀 ExpiredDomain.dev - EasyPanel Deployment Setup"
echo "=================================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your database credentials!"
    echo ""
fi

# Check if data directory exists
if [ ! -d "data/zones" ]; then
    echo "📁 Creating data directories..."
    mkdir -p data/zones
    echo "✅ Data directories created"
    echo ""
fi

# Check if alembic versions directory exists
if [ ! -d "alembic/versions" ]; then
    echo "📁 Creating Alembic versions directory..."
    mkdir -p alembic/versions
    touch alembic/versions/.gitkeep
    echo "✅ Alembic directory created"
    echo ""
fi

echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your database credentials"
echo "2. Push code to Git repository"
echo "3. Follow DEPLOY.md instructions for EasyPanel setup"
echo ""

