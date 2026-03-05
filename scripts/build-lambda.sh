#!/bin/bash

# Build Lambda function with dependencies
# Usage: ./scripts/build-lambda.sh <lambda-folder-name>

set -e

if [ -z "$1" ]; then
  echo "Usage: ./scripts/build-lambda.sh <lambda-folder-name>"
  echo "Example: ./scripts/build-lambda.sh email-config"
  exit 1
fi

LAMBDA_NAME=$1
LAMBDA_DIR="lambda/$LAMBDA_NAME"

if [ ! -d "$LAMBDA_DIR" ]; then
  echo "Error: Lambda directory $LAMBDA_DIR does not exist"
  exit 1
fi

if [ ! -f "$LAMBDA_DIR/requirements.txt" ]; then
  echo "No requirements.txt found in $LAMBDA_DIR, skipping dependency installation"
  exit 0
fi

echo "Building Lambda function: $LAMBDA_NAME"

# Create temporary virtual environment
TEMP_VENV=$(mktemp -d)
echo "Creating virtual environment in $TEMP_VENV"

python3 -m venv "$TEMP_VENV"
source "$TEMP_VENV/bin/activate"

# Install dependencies
echo "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r "$LAMBDA_DIR/requirements.txt" -t "$LAMBDA_DIR"

# Cleanup
deactivate
rm -rf "$TEMP_VENV"

echo "✅ Lambda function $LAMBDA_NAME built successfully"
echo "Dependencies installed in: $LAMBDA_DIR"
