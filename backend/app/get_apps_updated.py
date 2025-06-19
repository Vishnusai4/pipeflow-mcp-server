from typing import List, Dict, Tuple, Optional
import logging
import httpx
from fastapi import HTTPException, status
from .models.schema import AppInfo
from .constants import MCP_APPS, PIPEDREAM_API_KEY

logger = logging.getLogger(__name__)

async def get_apps_updated(request, current_user: str):
    """Get list of MCP apps with their logos and metadata"""
    
    async def fetch_from_pipedream() -> Tuple[bool, List[Dict]]:
        """Try to fetch apps from Pipedream API"""
        if not PIPEDREAM_API_KEY:
            logger.warning("PIPEDREAM_API_KEY not configured")
            return False, []

        endpoints_to_try = [
            "https://api.pipedream.com/v1/apps",
            "https://api.pipedream.com/v1/apps/list",
            "https://api.pipedream.com/v1/apps/all"
        ]
        
        for endpoint in endpoints_to_try:
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {PIPEDREAM_API_KEY}",
                    "Accept": "application/json"
                }
                
                logger.info(f"Trying endpoint: {endpoint}")
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        endpoint,
                        headers=headers,
                        params={"limit": 100},
                        timeout=10.0
                    )
                    
                    logger.debug(f"API response from {endpoint}: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        if 'data' in data and isinstance(data['data'], list):
                            return True, data['data']
                        logger.warning(f"Unexpected response format from {endpoint}")
                    
            except Exception as e:
                logger.warning(f"Failed to fetch from {endpoint}: {str(e)}")
        
        return False, []
    
    try:
        # First try to get apps from Pipedream API
        success, all_apps = await fetch_from_pipedream()
        
        if not success:
            logger.warning("Failed to fetch apps from Pipedream API, using fallback")
            raise Exception("Failed to fetch from Pipedream API")
                
    except Exception as e:
        logger.warning(f"Using fallback app list due to: {str(e)}")
        # Fallback to a static list of apps if API fails
        all_apps = [
            {
                "name": "GitHub", 
                "slug": "github",
                "description": "GitHub is a development platform for version control and collaboration.",
                "category": "version_control",
                "logo_url": "https://cdn.iconscout.com/icon/free/png-256/github-153-675523.png"
            },
            {
                "name": "GitLab",
                "slug": "gitlab",
                "description": "GitLab is a complete DevOps platform for software development.",
                "category": "version_control",
                "logo_url": "https://cdn.iconscout.com/icon/free/png-256/gitlab-3-1175054.png"
            },
            {
                "name": "Slack",
                "slug": "slack",
                "description": "Slack is a messaging platform for team communication.",
                "category": "communication",
                "logo_url": "https://cdn.iconscout.com/icon/free/png-256/slack-4054260-3353009.png"
            },
            {
                "name": "Jira",
                "slug": "jira",
                "description": "Jira is a project management tool for agile teams.",
                "category": "project_management",
                "logo_url": "https://cdn.iconscout.com/icon/free/png-256/jira-3628861-3030001.png"
            },
            {
                "name": "AWS",
                "slug": "aws",
                "description": "Amazon Web Services provides on-demand cloud computing platforms.",
                "category": "cloud",
                "logo_url": "https://cdn.iconscout.com/icon/free/png-256/aws-1869025-1583149.png"
            },
            {
                "name": "Google Cloud",
                "slug": "google_cloud",
                "description": "Google Cloud offers cloud computing services.",
                "category": "cloud",
                "logo_url": "https://cdn.iconscout.com/icon/free/png-256/google-cloud-platform-2038785-1721675.png"
            },
            {
                "name": "Azure",
                "slug": "azure",
                "description": "Microsoft Azure is a cloud computing service.",
                "category": "cloud",
                "logo_url": "https://cdn.iconscout.com/icon/free/png-256/microsoft-azure-2038745-1721658.png"
            },
            {
                "name": "Datadog",
                "slug": "datadog",
                "description": "Datadog is a monitoring and analytics platform.",
                "category": "monitoring",
                "logo_url": "https://cdn.iconscout.com/icon/free/png-256/datadog-3628878-3029824.png"
            },
            {
                "name": "New Relic",
                "slug": "new_relic",
                "description": "New Relic provides application performance monitoring.",
                "category": "monitoring",
                "logo_url": "https://cdn.iconscout.com/icon/free/png-256/new-relic-3628878-3029817.png"
            },
            {
                "name": "MongoDB",
                "slug": "mongodb",
                "description": "MongoDB is a NoSQL database program.",
                "category": "database",
                "logo_url": "https://cdn.iconscout.com/icon/free/png-256/mongodb-3629020-3030245.png"
            },
            {
                "name": "PostgreSQL",
                "slug": "postgresql",
                "description": "PostgreSQL is a powerful open-source relational database.",
                "category": "database",
                "logo_url": "https://cdn.iconscout.com/icon/free/png-256/postgresql-3628899-3030131.png"
            },
            {
                "name": "MySQL",
                "slug": "mysql",
                "description": "MySQL is an open-source relational database management system.",
                "category": "database",
                "logo_url": "https://cdn.iconscout.com/icon/free/png-256/mysql-3628940-3030164.png"
            },
            {
                "name": "Docker",
                "slug": "docker",
                "description": "Docker is a platform for developing, shipping, and running applications in containers.",
                "category": "containerization",
                "logo_url": "https://cdn.iconscout.com/icon/free/png-256/docker-3629025-3030155.png"
            },
            {
                "name": "Kubernetes",
                "slug": "kubernetes",
                "description": "Kubernetes is an open-source container orchestration platform.",
                "category": "orchestration",
                "logo_url": "https://cdn.iconscout.com/icon/free/png-256/kubernets-2949129-2441984.png"
            }
        ]
            
    # Process the apps we got (either from API or fallback)
    processed_apps = []
    for app in all_apps:
        try:
            # Skip apps that don't have a name
            if not app.get('name'):
                continue
                
            # Generate slug from name if not provided
            slug = app.get('slug', app['name'].lower().replace(' ', '_'))
            
            # Create AppInfo object with proper error handling
            app_info = {
                "name": app.get('name', ''),
                "slug": slug,
                "description": app.get('description', f"Integration with {app['name']}"),
                "category": app.get('category', 'other'),
                "logo_url": app.get('logo_url') or app.get('icon_url', ''),
                "is_connected": False,  # Default to not connected
                "tools_count": 0  # Default tools count
            }
            
            # Validate the app info against the model
            validated_app = AppInfo(**app_info)
            processed_apps.append(validated_app)
            
        except Exception as e:
            logger.warning(f"Error processing app {app.get('name', 'unknown')}: {str(e)}")
            continue
    
    # Filter to only include MCP apps
    mcp_apps = [
        app for app in processed_apps 
        if app.name.lower() in [a.lower() for a in MCP_APPS]
    ]
    
    logger.info(f"Returning {len(mcp_apps)} MCP apps")
    return mcp_apps
