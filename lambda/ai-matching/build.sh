#!/bin/bash
# Build script for AI Matching Lambda function

set -e

echo "Building AI Matching Lambda function..."

# Create build directory
rm -rf build
mkdir -p build

# Copy Lambda function code
cp index.py build/
cp requirements.txt build/

# Install dependencies to build directory
pip install -r requirements.txt -t build/ --platform manylinux2014_aarch64 --only-binary=:all:

echo "Build complete! Package is in build/"
echo "To deploy: cd ../../infrastructure && cdk deploy"
