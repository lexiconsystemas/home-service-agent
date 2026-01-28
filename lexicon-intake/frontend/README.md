# Lexicon Dashboard Frontend

Production-ready dashboard for the Lexicon Home Services Intake System.

## Development

### Prerequisites
- Node.js 18+ 
- npm or yarn

### Setup
```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Start development server
npm run dev
```

### Environment Variables
Create a `.env` file with:
```env
VITE_API_URL=http://localhost:8000
```

## Production Deployment

### Vercel Deployment
The frontend is configured for Vercel deployment with:

1. **Automatic Configuration**: `vercel.json`
2. **Production Environment**: `.env.production`
3. **Optimized Build**: `vite.config.ts` with code splitting

#### Deploy to Vercel:
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

### Environment Configuration
- **Development**: Uses `VITE_API_URL=http://localhost:8000`
- **Production**: Uses `VITE_API_URL=https://lexicon-intake-production.up.railway.app`

### Build Configuration
- **Output Directory**: `dist/`
- **Framework**: Vite
- **Code Splitting**: Optimized chunks for vendor libraries
- **Source Maps**: Disabled in production

## Features
- **Real-time Dashboard** with live metrics
- **Authentication** with API key validation
- **React Query** for data fetching and caching
- **Responsive Design** for all screen sizes
- **TypeScript** for type safety
- **Tailwind CSS** for styling

## Scripts
```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run preview  # Preview production build
```

## Architecture
- **React 18** with TypeScript
- **React Router** for navigation
- **React Query** for API state management
- **Axios** for HTTP requests
- **Tailwind CSS** for styling
- **Lucide React** for icons
- **Recharts** for data visualization