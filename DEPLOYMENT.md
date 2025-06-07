# 🚀 EssenceMirror Deployment Guide

## Quick Deployment Options

### 1. 🌟 Streamlit Cloud (Easiest - Recommended)

**Steps:**
1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Add secrets in dashboard
5. Deploy!

**Secrets to add in Streamlit Cloud:**
```toml
AWS_ACCESS_KEY_ID = "your_aws_access_key"
AWS_SECRET_ACCESS_KEY = "your_aws_secret_key"
AWS_DEFAULT_REGION = "us-east-1"
S3_BUCKET = "essencemirror-user-uploads"
AGENT_ID = "WWIUY28GRY"
AGENT_ALIAS_ID = "TSTALIASID"
```

**Pros:**
- ✅ Free hosting
- ✅ Automatic deployments
- ✅ Built-in secrets management
- ✅ SSL included
- ✅ No server management

### 2. 🐳 Docker Deployment

**Build and run:**
```bash
docker build -t essence-mirror .
docker run -p 8501:8501 \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  -e S3_BUCKET=essencemirror-user-uploads \
  -e AGENT_ID=WWIUY28GRY \
  -e AGENT_ALIAS_ID=TSTALIASID \
  essence-mirror
```

### 3. ☁️ AWS ECS/Fargate

**Deploy containerized app:**
1. Push Docker image to ECR
2. Create ECS task definition
3. Configure service with IAM roles
4. Use Application Load Balancer

### 4. 🟣 Heroku

**Deploy steps:**
```bash
heroku create essence-mirror-app
heroku config:set AWS_ACCESS_KEY_ID=your_key
heroku config:set AWS_SECRET_ACCESS_KEY=your_secret
heroku config:set S3_BUCKET=essencemirror-user-uploads
heroku config:set AGENT_ID=WWIUY28GRY
heroku config:set AGENT_ALIAS_ID=TSTALIASID
git push heroku main
```

### 5. 🔵 DigitalOcean App Platform

**One-click deployment:**
1. Connect GitHub repo
2. Configure environment variables
3. Deploy automatically

## 🔧 Configuration for Production

### Environment Variables Required:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION`
- `S3_BUCKET`
- `AGENT_ID`
- `AGENT_ALIAS_ID`

### Security Best Practices:
1. **Use IAM roles** instead of access keys when possible
2. **Restrict S3 bucket permissions** to specific operations
3. **Enable HTTPS** in production
4. **Set up monitoring** and logging

## 🎯 Recommended: Streamlit Cloud

For the fastest deployment with minimal setup:

1. **Create GitHub repo** and push your code
2. **Go to Streamlit Cloud** and connect repo
3. **Add secrets** in the dashboard
4. **Deploy** - your app will be live in minutes!

Your app will be available at: `https://your-app-name.streamlit.app`

## 🔍 Testing Deployment

After deployment, test these features:
- ✅ Image upload and analysis
- ✅ Recommendations generation
- ✅ Chat functionality
- ✅ Profile updates
- ✅ Session management

## 📊 Monitoring

- **Streamlit Cloud**: Built-in analytics
- **AWS CloudWatch**: Monitor Bedrock usage
- **Application logs**: Check for errors

## 🆘 Troubleshooting

**Common issues:**
- AWS credentials not configured
- Bedrock permissions missing
- S3 bucket access denied
- Dependencies not installed

**Debug steps:**
1. Check application logs
2. Verify environment variables
3. Test AWS connectivity
4. Validate Bedrock agent status
