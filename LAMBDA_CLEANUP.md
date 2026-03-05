# Lambda Directory Cleanup

## Problem

When installing Python dependencies for Lambda functions using `pip install -t .`, all the dependency files were installed directly in the lambda directories, creating a mess of folders and files that shouldn't be committed to git.

## Solution

### 1. Cleaned Up Directories

Removed all installed dependencies from `lambda/email-config/`:
- boto3/
- botocore/
- s3transfer/
- jmespath/
- dateutil/
- urllib3/
- bin/
- *.dist-info/
- six.py

Now each Lambda directory only contains:
- `index.py` (source code)
- `requirements.txt` (dependency list)

### 2. Updated .gitignore

Added comprehensive rules to ignore Lambda dependencies:

```gitignore
# Lambda Python dependencies (installed via pip install -t)
lambda/**/boto3/
lambda/**/boto3-*/
lambda/**/botocore/
lambda/**/botocore-*/
lambda/**/s3transfer/
lambda/**/s3transfer-*/
lambda/**/jmespath/
lambda/**/jmespath-*/
lambda/**/dateutil/
lambda/**/python_dateutil-*/
lambda/**/urllib3/
lambda/**/urllib3-*/
lambda/**/six.py
lambda/**/six-*/
lambda/**/bin/
lambda/**/*.dist-info/
```

### 3. Created Build Scripts

#### Single Lambda Build
`scripts/build-lambda.sh <lambda-name>`

Uses a temporary virtual environment to install dependencies cleanly.

#### All Lambdas Build
`scripts/build-all-lambdas.sh`

Builds all Lambda functions with Python dependencies in one command.

### 4. Added Documentation

Created `lambda/README.md` with:
- How to build Lambda functions
- Why dependencies aren't committed
- Best practices
- Troubleshooting guide

## Why Use Virtual Environments?

✅ **Clean installation** - No pollution of system Python
✅ **Isolated dependencies** - Each Lambda gets exactly what it needs
✅ **Reproducible builds** - Same result every time
✅ **Easy cleanup** - Just delete the temp venv

## Deployment Workflow

### Before Deployment

```bash
# Build all Lambda functions
./scripts/build-all-lambdas.sh

# Deploy with CDK
cdk deploy ReconcileAI-dev
```

### What Happens

1. Build script creates temp venv for each Lambda
2. Installs dependencies from requirements.txt
3. Copies dependencies to Lambda directory
4. Cleans up temp venv
5. CDK packages Lambda with dependencies
6. Deploys to AWS

### After Deployment

Dependencies remain in Lambda directories (gitignored) until you:
- Run `git clean -fdx` (removes all gitignored files)
- Manually delete them
- Rebuild before next deployment

## Benefits

✅ **Clean repository** - No 100+ MB of dependencies in git
✅ **Faster git operations** - Smaller repo size
✅ **Better collaboration** - No merge conflicts in dependency files
✅ **Platform independence** - Dependencies installed fresh each time
✅ **Clear separation** - Source code vs dependencies

## Current State

- ✅ Lambda directories cleaned
- ✅ .gitignore updated
- ✅ Build scripts created
- ✅ Documentation added
- ✅ All Lambda functions deployable

## Next Steps

When adding new Lambda functions:

1. Create directory: `lambda/new-function/`
2. Add source: `lambda/new-function/index.py`
3. Add deps: `lambda/new-function/requirements.txt`
4. Build: `./scripts/build-lambda.sh new-function`
5. Deploy: `cdk deploy`

Dependencies will be automatically gitignored! 🎉
