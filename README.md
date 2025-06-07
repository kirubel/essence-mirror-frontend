# 🌟 EssenceMirror Frontend

A beautiful, interactive web application for personal style analysis and recommendations powered by Amazon Bedrock and Nova Pro AI.

## ✨ Features

- **📸 Image Analysis**: Upload photos for AI-powered style analysis
- **🎯 Personalized Recommendations**: Get tailored lifestyle suggestions
- **💬 Interactive Chat**: Converse with your AI style advisor
- **⚙️ Profile Management**: Update preferences and settings
- **🚀 Quick Actions**: Focus on specific recommendation areas
- **📱 Responsive Design**: Works on desktop and mobile

## 🚀 Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd essence-mirror-frontend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure AWS credentials**
   ```bash
   aws configure
   # OR set environment variables
   export AWS_ACCESS_KEY_ID=your_key
   export AWS_SECRET_ACCESS_KEY=your_secret
   export AWS_DEFAULT_REGION=us-east-1
   ```

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

5. **Open in browser**
   Navigate to `http://localhost:8501`

## 🌐 Production Deployment

### Option 1: Streamlit Cloud (Recommended)

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **Deploy on Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub repository
   - Configure secrets in the Streamlit Cloud dashboard
   - Deploy with one click

3. **Configure Secrets**
   In Streamlit Cloud dashboard, add these secrets:
   ```toml
   AWS_ACCESS_KEY_ID = "your_aws_access_key"
   AWS_SECRET_ACCESS_KEY = "your_aws_secret_key"
   AWS_DEFAULT_REGION = "us-east-1"
   S3_BUCKET = "essencemirror-user-uploads"
   AGENT_ID = "WWIUY28GRY"
   AGENT_ALIAS_ID = "TSTALIASID"
   ```

### Option 2: AWS EC2/ECS

1. **Create Docker container** (optional)
2. **Deploy to EC2 instance**
3. **Use IAM roles for AWS access**
4. **Configure load balancer and SSL**

### Option 3: Heroku

1. **Create Procfile**
2. **Configure buildpacks**
3. **Set environment variables**
4. **Deploy via Git**

## 🔧 Configuration

### Environment Variables

- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `AWS_DEFAULT_REGION`: AWS region (default: us-east-1)
- `S3_BUCKET`: S3 bucket for image uploads
- `AGENT_ID`: Bedrock agent ID
- `AGENT_ALIAS_ID`: Bedrock agent alias ID

### Streamlit Configuration

The app includes custom configuration in `.streamlit/config.toml`:
- Custom theme colors
- Server settings
- Browser preferences

## 📁 Project Structure

```
essence-mirror-frontend/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── .streamlit/
│   ├── config.toml       # Streamlit configuration
│   └── secrets.toml      # Secrets template
├── .gitignore            # Git ignore rules
└── assets/               # Static assets (if any)
```

## 🛠️ Development

### Adding New Features

1. **Create new tabs** in the main app
2. **Add new functions** for specific features
3. **Update session state** management
4. **Test locally** before deployment

### Customization

- **Styling**: Modify `.streamlit/config.toml`
- **Layout**: Update the tab structure in `app.py`
- **Features**: Add new interaction patterns
- **Branding**: Update titles, icons, and messaging

## 🔒 Security

- **Never commit secrets** to version control
- **Use environment variables** for sensitive data
- **Configure IAM roles** with minimal permissions
- **Enable HTTPS** in production

## 📊 Monitoring

- **Streamlit Cloud**: Built-in analytics
- **AWS CloudWatch**: Monitor Bedrock usage
- **Custom logging**: Add application logs

## 🐛 Troubleshooting

### Common Issues

1. **AWS Credentials**: Ensure proper AWS configuration
2. **Bedrock Permissions**: Check IAM policies
3. **S3 Access**: Verify bucket permissions
4. **Dependencies**: Update requirements.txt

### Debug Mode

Add debug information:
```python
st.write("Debug info:", st.session_state)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
- Check the troubleshooting section
- Review AWS Bedrock documentation
- Contact the development team

---

*Powered by Amazon Bedrock, Nova Pro AI, and Streamlit* ✨
