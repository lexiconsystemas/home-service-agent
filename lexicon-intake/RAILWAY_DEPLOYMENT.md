# Railway Deployment Guide

## 🚀 Deploy Lexicon Intake System to Railway

### Prerequisites
- Railway account
- Railway CLI installed (`npm install -g @railway/cli`)
- Git repository with the code

### Step 1: Initialize Railway Project

```bash
# Login to Railway
railway login

# Initialize project in your repository
cd lexicon-intake
railway init
```

### Step 2: Add Railway Services

```bash
# Add web service
railway add --name web

# Add worker service
railway add --name worker
```

### Step 3: Configure Database

```bash
# Add PostgreSQL addon
railway add postgresql

# Add Redis addon
railway add redis
```

### Step 4: Set Environment Variables

```bash
# Set required environment variables
railway variables set SECRET_KEY=your-production-secret-key
railway variables set WEBHOOK_SIGNING_SECRET=your-production-webhook-secret
railway variables set ADMIN_API_KEY=your-production-admin-api-key
railway variables set TWILIO_AUTH_TOKEN=your-twilio-auth-token
railway variables set SENDGRID_API_KEY=your-sendgrid-api-key
railway variables set LOG_LEVEL=INFO
```

### Step 5: Deploy

```bash
# Deploy to Railway
railway up
```

### Step 6: Configure Services

#### Web Service Configuration:
- **Build Command**: `pip install -e .`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Port**: 8000
- **Health Check**: `/`

#### Worker Service Configuration:
- **Build Command**: `pip install -e .`
- **Start Command**: `python -m app.workers`
- **No port required**

### Environment Variables Required

| Variable | Source | Description |
|----------|--------|-------------|
| `DATABASE_URL` | Railway Postgres addon | Database connection |
| `REDIS_URL` | Railway Redis addon | Redis connection |
| `SECRET_KEY` | Manual | Application secret |
| `WEBHOOK_SIGNING_SECRET` | Manual | Webhook verification |
| `ADMIN_API_KEY` | Manual | Admin endpoint access |
| `TWILIO_AUTH_TOKEN` | Manual | Twilio SMS |
| `SENDGRID_API_KEY` | Manual | SendGrid email |
| `LOG_LEVEL` | Manual | Logging level |
| `PORT` | Railway | Application port |

### Verification

After deployment:

1. **Web Service**: Check the web URL provided by Railway
2. **Health Check**: Visit `https://your-app.railway.app/`
3. **API Docs**: Visit `https://your-app.railway.app/docs`
4. **Worker Logs**: Check Railway dashboard for worker status

### Troubleshooting

#### Common Issues:

1. **Database Connection Errors**
   - Ensure DATABASE_URL is properly set
   - Check Railway Postgres addon status

2. **Worker Not Starting**
   - Verify worker service configuration
   - Check worker logs in Railway dashboard

3. **Import Errors**
   - Ensure all dependencies are in pyproject.toml
   - Check build logs for missing packages

4. **Port Issues**
   - Ensure PORT environment variable is set
   - Use $PORT in start command

#### Logs Monitoring:

```bash
# View web service logs
railway logs web

# View worker service logs
railway logs worker

# View all logs
railway logs
```

### Production Considerations

1. **Security**: Use strong, unique secrets
2. **Monitoring**: Set up Railway alerts
3. **Backups**: Enable automatic database backups
4. **Scaling**: Configure auto-scaling if needed
5. **Domain**: Add custom domain in Railway settings

### Railway Configuration Files

- `railway.toml`: Service definitions and build configuration
- `Procfile`: Process definitions (web and worker)
- `.env.railway`: Environment variable template

### Post-Deployment Checklist

- [ ] Web service responding correctly
- [ ] Worker service running without errors
- [ ] Database migrations applied
- [ ] All environment variables set
- [ ] Health checks passing
- [ ] API endpoints accessible
- [ ] Logs showing normal operation
