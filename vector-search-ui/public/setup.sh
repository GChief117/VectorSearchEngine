#!/bin/bash

# Enterprise Vector Search UI Setup Script
# For SentinelOne Interview Project

set -e

echo "🚀 Setting up Enterprise Vector Search UI..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

if ! command_exists node; then
    echo -e "${RED}❌ Node.js is not installed. Please install Node.js 16+${NC}"
    exit 1
fi

if ! command_exists npm; then
    echo -e "${RED}❌ npm is not installed. Please install npm${NC}"
    exit 1
fi

if ! command_exists python3; then
    echo -e "${RED}❌ Python 3 is not installed. Please install Python 3.8+${NC}"
    exit 1
fi

if ! command_exists poetry; then
    echo -e "${RED}❌ Poetry is not installed. Installing...${NC}"
    pip3 install poetry
fi

echo -e "${GREEN}✅ Prerequisites checked${NC}"

# Navigate to project directory
cd ~/Desktop/sone/interview-GChief117

# Create React TypeScript app
echo -e "${BLUE}Creating React TypeScript app...${NC}"
if [ ! -d "vector-search-ui" ]; then
    npx create-react-app vector-search-ui --template typescript
fi

cd vector-search-ui

# Install dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
npm install axios @mui/material @emotion/react @emotion/styled @mui/icons-material recharts @reduxjs/toolkit react-redux socket.io-client

# Install dev dependencies
npm install --save-dev @types/node concurrently eslint prettier source-map-explorer webpack-bundle-analyzer serve

# Copy the App.tsx and other files from artifacts
echo -e "${BLUE}Setting up application files...${NC}"

# Create src/App.tsx (copy from artifact)
echo "Please copy the App.tsx content from the artifact above to src/App.tsx"

# Create package.json (copy from artifact)
echo "Please copy the package.json content from the artifact above"

# Create directories
mkdir -p src/components src/services src/hooks src/types src/utils

# Create tsconfig.json for strict TypeScript
cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "noFallthroughCasesInSwitch": true,
    "module": "esnext",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"]
}
EOF

# Create .env file
cat > .env << 'EOF'
REACT_APP_API_URL=http://localhost:8000
REACT_APP_ENABLE_ANALYTICS=false
REACT_APP_WEBSOCKET_URL=ws://localhost:8000/ws
EOF

# Create .prettierrc
cat > .prettierrc << 'EOF'
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false
}
EOF

# Create .eslintrc.json
cat > .eslintrc.json << 'EOF'
{
  "extends": [
    "react-app",
    "react-app/jest",
    "prettier"
  ],
  "rules": {
    "no-console": "warn",
    "@typescript-eslint/no-unused-vars": "error",
    "react-hooks/exhaustive-deps": "warn"
  }
}
EOF

# Update backend with Redis support
echo -e "${BLUE}Updating backend with Redis support...${NC}"
cd ../embedding_server

# Add Redis dependencies
poetry add redis aioredis

# Copy redis_cache.py from artifact
echo "Please copy the redis_cache.py content from the artifact to src/embedding_server/redis_cache.py"

# Copy updated server.py from artifact
echo "Please copy the updated server.py content from the artifact to src/embedding_server/server.py"

# Check if Docker is installed for Redis
if command_exists docker; then
    echo -e "${BLUE}Starting Redis with Docker...${NC}"
    docker run -d -p 6379:6379 --name redis-vector-search redis:alpine || echo "Redis container already exists"
else
    echo -e "${RED}Docker not found. Please install Redis manually or install Docker${NC}"
fi

echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Copy the artifact contents to the appropriate files"
echo "2. Start the backend: cd embedding_server && poetry run python -m embedding_server.server"
echo "3. Start the frontend: cd vector-search-ui && npm start"
echo "4. Open http://localhost:3000 in your browser"
echo ""
echo "For concurrent development:"
echo "cd vector-search-ui && npm run dev"