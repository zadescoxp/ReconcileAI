#!/bin/bash
# Build script for PDF Extraction Lambda with dependencies

set -e

echo "Building PDF Extraction Lambda..."

# Create a clean build directory
rm -rf package
mkdir -p package

# Install dependencies to package directory
pip install -r requirements.txt -t package/ --platform manylinux2014_aarch64 --only-binary=:all:

# Copy Lambda function code
cp index.py package/

# Create deployment package
cd package
zip -r ../lambda-package.zip .
cd ..

echo "Build complete! Deployment package: lambda-package.zip"
