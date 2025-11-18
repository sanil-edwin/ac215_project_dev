# Frontend Dashboard

**Next.js 14 application with 4 core components**

## Files

- `src/app/page.tsx` - Main dashboard
- `src/components/` - 4 React components
- `package.json` - Node dependencies
- `Dockerfile` - Container definition

## Components

1. **CountySelector** - Dropdown of 99 Iowa counties
2. **MCSIDisplay** - Real-time stress visualization
3. **YieldPredictor** - Yield predictions
4. **HistoricalChart** - Trend charts

## Setup

### 1. Install Dependencies
```bash
npm install
```

### 2. Set API URL
```bash
# Create .env.local file
echo "NEXT_PUBLIC_API_URL=http://localhost:8080" > .env.local

# Or use your deployed API URL
echo "NEXT_PUBLIC_API_URL=https://your-api-url.run.app" > .env.local
```

### 3. Run Development Server
```bash
npm run dev
# Visit http://localhost:3000
```

### 4. Build for Production
```bash
npm run build
npm start
```

### 5. Deploy
```bash
# Use deployment scripts in ../deployment/
cd ../deployment
./deploy.sh
```

## Technology

- Next.js 14
- TypeScript
- Tailwind CSS
- Recharts
- Axios
- Runs on port 3000
