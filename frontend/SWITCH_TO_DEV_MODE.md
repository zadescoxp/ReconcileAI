# Switch to Development Mode (No Authentication)

## Windows Commands

```powershell
# Navigate to frontend/src
cd frontend\src

# Backup production file
ren index.tsx index-prod.tsx

# Activate development file
ren index-dev.tsx index.tsx

# Go back and start
cd ..\..
cd frontend
npm start
```

## Mac/Linux Commands

```bash
# Navigate to frontend/src
cd frontend/src

# Backup production file
mv index.tsx index-prod.tsx

# Activate development file
mv index-dev.tsx index.tsx

# Go back and start
cd ../..
cd frontend
npm start
```

## What This Does

- Saves your production `index.tsx` as `index-prod.tsx`
- Renames `index-dev.tsx` to `index.tsx` (activates dev mode)
- Starts the app without AWS authentication

## Open Browser

http://localhost:3000

You'll see the full UI with mock data and no login required!

---

# Switch Back to Production Mode

## Windows Commands

```powershell
cd frontend\src
ren index.tsx index-dev.tsx
ren index-prod.tsx index.tsx
cd ..\..
```

## Mac/Linux Commands

```bash
cd frontend/src
mv index.tsx index-dev.tsx
mv index-prod.tsx index.tsx
cd ../..
```

## Done!

Production mode with authentication is restored.
