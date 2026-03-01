#!/bin/bash
# Switch to production mode (requires AWS)

echo "Switching to production mode..."

# Restore production index
if [ -f "src/index-prod.tsx" ]; then
    cp src/index-prod.tsx src/index.tsx
    echo "✓ Restored production index.tsx"
else
    echo "✗ No production backup found (index-prod.tsx)"
    exit 1
fi

echo ""
echo "Production mode activated! Run: npm start"
echo "To switch back to development mode, run: ./switch-to-dev.sh"
