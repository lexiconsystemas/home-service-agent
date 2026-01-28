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

### Netlify Deployment
The frontend is configured for Netlify deployment with:

1. **Automatic Configuration**: `netlify.toml`
2. **Production Environment**: `.env.production`
3. **Optimized Build**: `vite.config.ts` with code splitting
4. **Build Script**: `netlify-build.sh` for custom builds

#### Deploy to Netlify:
```bash
# Install Netlify CLI
npm i -g netlify-cli

# Login to Netlify
netlify login

# Deploy to production
netlify deploy --prod --dir=dist

# Or connect to Git for automatic deployments
netlify init
git push origin main
```

#### Manual Build:
```bash
# Make build script executable
chmod +x netlify-build.sh

# Run build script
./netlify-build.sh
```

### Environment Configuration
- **Development**: Uses `VITE_API_URL=http://localhost:8000`
- **Production**: Uses `VITE_API_URL=https://lexicon-intake-production.up.railway.app`
- **Deploy Previews**: Uses production API URL for testing

### Build Configuration
- **Output Directory**: `dist/`
- **Framework**: Vite
- **Node Version**: 18 (required by Netlify)
- **Code Splitting**: Optimized chunks for vendor libraries
- **Source Maps**: Disabled in production
- **SPA Routing**: All routes redirect to `index.html`

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