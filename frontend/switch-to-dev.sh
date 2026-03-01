#!/bin/bash
# Switch to development mode (no AWS required)

echo "Switching to development mode..."

# Backup production index if it exists
if [ -f "src/index.tsx" ] && [ ! -f "src/index-prod.tsx" ]; then
    mv src/index.tsx src/index-prod.tsx
    echo "✓ Backed up production index.tsx to index-prod.tsx"
fi

# Copy dev index to main index
cp src/index-dev.tsx src/index.tsx
echo "✓ Activated development mode"

echo ""
echo "Development mode activated! Run: npm start"
echo "To switch back to production mode, run: ./switch-to-prod.sh"
