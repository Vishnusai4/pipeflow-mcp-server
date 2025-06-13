# Hardcoded credentials (use proper management in production)
USERS = {
    "admin": "admin",
    "user1": "mypassword",
    "demo": "demo123"
}

# MCP-supported apps list
MCP_APPS = [
    'GitHub', 'GitLab', 'Bitbucket', 'Azure DevOps', 'Amazon Web Services',
    'Google Cloud Platform', 'Microsoft Azure', 'DigitalOcean', 'Grafana',
    'Prometheus', 'Datadog', 'New Relic', 'Logz.io', 'Sentry', 'Slack',
    'Microsoft Teams', 'Discord', 'Jira', 'Asana', 'Linear', 'Notion',
    'Zendesk', 'Intercom', 'Jenkins', 'CircleCI', 'GitHub Actions',
    'Snyk', 'SonarQube', 'MongoDB Atlas', 'Redis Enterprise', 'Postman', 'Cypress'
]

# Pipedream configuration from environment

PIPEDREAM_CLIENT_ID = "OH2gtI6wts6OPGXRTVJ7DUdqyz2HOJuJtWZZnrzcNo4"
PIPEDREAM_CLIENT_SECRET = "JAZzrzjOz0oOyLrxuPG6h_60WjtIFlDhtzi_SsPdaHU"
PIPEDREAM_PROJECT_ID = "proj_JPsmDZ9"
PIPEDREAM_ENVIRONMENT = "development"


SECRET_KEY = "your-secret-key-change-in-production"  # Change in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
