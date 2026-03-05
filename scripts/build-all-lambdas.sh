#!/bin/bash

# Build all Lambda functions with Python dependencies
# This script uses virtual environments to avoid polluting the lambda directories

set -e

echo "🔨 Building all Lambda functions..."
echo ""

# List of Lambda functions with Python dependencies
PYTHON_LAMBDAS=(
  "email-config"
  "pdf-extraction"
  "ai-matching"
  "fraud-detection"
  "resolve-step"
  "po-management"
  "invoice-management"
  "audit-logs"
)

for lambda_name in "${PYTHON_LAMBDAS[@]}"; do
  lambda_dir="lambda/$lambda_name"
  
  if [ ! -d "$lambda_dir" ]; then
    echo "⚠️  Skipping $lambda_name (directory not found)"
    continue
  fi
  
  if [ ! -f "$lambda_dir/requirements.txt" ]; then
    echo "⚠️  Skipping $lambda_name (no requirements.txt)"
    continue
  fi
  
  echo "📦 Building $lambda_name..."
  
  # Create temporary virtual environment
  temp_venv=$(mktemp -d)
  
  # Create venv and install dependencies
  python3 -m venv "$temp_venv" > /dev/null 2>&1
  source "$temp_venv/bin/activate"
  
  pip install --quiet --upgrade pip > /dev/null 2>&1
  pip install --quiet -r "$lambda_dir/requirements.txt" -t "$lambda_dir" > /dev/null 2>&1
  
  # Cleanup venv
  deactivate
  rm -rf "$temp_venv"
  
  echo "   ✅ $lambda_name built"
done

echo ""
echo "✨ All Lambda functions built successfully!"
echo ""
echo "Note: Dependencies are installed directly in lambda folders for CDK deployment"
echo "They are gitignored and will not be committed to the repository"
