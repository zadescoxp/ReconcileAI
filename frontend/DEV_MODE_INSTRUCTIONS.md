# Frontend Development Mode

Run the ReconcileAI frontend locally without AWS deployment!

## Quick Start (Windows)

### Option 1: Manual Switch (Easiest)

1. **Navigate to frontend/src directory**
2. **Rename files:**
   ```bash
   # Backup production version
   ren index.tsx index-prod.tsx
   
   # Activate dev version
   copy index-dev.tsx index.tsx
   ```

3. **Start the app:**
   ```bash
   cd frontend
   npm install
   npm start
   ```

4. **Open browser:** http://localhost:3000

### Option 2: Use Git Bash (If you have it)

```bash
cd frontend
chmod +x switch-to-dev.sh
./switch-to-dev.sh
npm start
```

## What You'll See

✅ **Full UI Preview** - All components and styling
✅ **Navigation** - Switch between Dashboard, PO Upload, Invoices, etc.
✅ **No AWS Required** - Works completely offline
✅ **Hot Reload** - Changes update instantly

## Available Pages

- **Dashboard** - Overview with stats
- **Upload PO** - Purchase order upload form
- **Search POs** - Search and filter purchase orders
- **Invoices** - Invoice list with status filters
- **Invoice Detail** - Detailed invoice view with approval actions
- **Audit Trail** - System activity logs

## Switching Back to Production Mode

### Windows:
```bash
cd frontend/src
ren index.tsx index-dev.tsx
ren index-prod.tsx index.tsx
```

### Git Bash:
```bash
cd frontend
./switch-to-prod.sh
```

## Troubleshooting

### "Module not found" errors
```bash
cd frontend
npm install
```

### Port 3000 already in use
```bash
# Kill the process or use a different port
set PORT=3001
npm start
```

### TypeScript errors
The errors you saw are now fixed! Just make sure you're using the dev mode files.

## Development Tips

1. **Mock Data**: Components will show placeholder data when API calls fail
2. **Styling**: All CSS is loaded, so you can see the full design
3. **Components**: Test UI interactions without backend
4. **Fast Iteration**: Make changes and see them instantly

## Files Structure

```
frontend/src/
├── index.tsx           # Current active entry point
├── index-prod.tsx      # Production entry (with AWS auth)
├── index-dev.tsx       # Development entry (no AWS)
├── App.tsx             # Production app
└── DevApp.tsx          # Development app
```

## Need Help?

- Check the browser console for any errors
- Make sure all dependencies are installed: `npm install`
- Try clearing cache: Delete `node_modules` and run `npm install` again
