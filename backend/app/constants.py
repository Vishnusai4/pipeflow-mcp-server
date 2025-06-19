# Hardcoded credentials (use proper management in production)
import os

USERS = {
    "admin": "admin",
    "user1": "mypassword",
    "demo": "demo123"
}

# MCP-supported apps list
MCP_APPS = [
    'GitHub', 'GitLab', 'Bitbucket', 'Azure DevOps', 'AWS',
    'Google Cloud', 'Microsoft Azure SQL Database', 'Azure Storage', 'DigitalOcean', 'Grafana',
    'Datadog', 'New Relic', 'Sentry', 'Slack',
    'Microsoft Teams', 'Discord', 'Jira', 'Asana', 'Linear (OAuth)', 'Notion',
    'Zendesk', 'Intercom', 'Jenkins', 'CircleCI',
    'Snyk', 'SonarCloud', 'MongoDB', 'Upstash Redis', 'Postman',
    'Microsoft Outlook', 'Gmail'
]

# Pipedream configuration from environment
PIPEDREAM_API_KEY = "pdc_OH2gtI6wts6OPGXRTVJ7DUdqyz2HOJuJtWZZnrzcNo4"  # Example format
PIPEDREAM_CLIENT_ID = "OH2gtI6wts6OPGXRTVJ7DUdqyz2HOJuJtWZZnrzcNo4"
PIPEDREAM_CLIENT_SECRET = "JAZzrzjOz0oOyLrxuPG6h_60WjtIFlDhtzi_SsPdaHU"
PIPEDREAM_PROJECT_ID = "proj_JPsmDZ9"
PIPEDREAM_ENVIRONMENT = "development"


SECRET_KEY = "your-secret-key-change-in-production"  # Change in production
REFRESH_SECRET_KEY = "your-refresh-secret-key-change-in-production"  # Change in production
ALGORITHM = "HS256"
# Increased for testing
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day
REFRESH_TOKEN_EXPIRE_DAYS = 7  # Refresh token expires in 7 days

#APP_FILE_PATH = "app.apps.json"

APP_FILE_PATH = os.path.join(os.path.dirname(__file__), "app_info.json")

# Frontend URL for OAuth callbacks
APP_URL = os.getenv("APP_URL", "http://localhost:3000")
