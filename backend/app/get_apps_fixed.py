from typing import List, Dict, Optional, Tuple
from fastapi import Request, HTTPException
from jose import JWTError, jwt
import logging
import httpx
from .models.schema import AppInfo
from .constants import MCP_APPS, PIPEDREAM_API_KEY

logger = logging.getLogger(__name__)

async def get_apps_fixed(request: Request, current_user: str):
    """Fixed version of get_apps function with proper error handling"""
    
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
            # Fallback to a static list of apps if API fails
            all_apps = [
                {"name": "GitHub", "icon_url": "https://cdn.iconscout.com/icon/free/png-256/github-153-675523.png"},
                {"name": "GitLab", "icon_url": "https://cdn.iconscout.com/icon/free/png-256/gitlab-3-1175054.png"},
                {"name": "Slack", "icon_url": "https://cdn.iconscout.com/icon/free/png-256/slack-4054260-3353009.png"},
                {"name": "Jira", "icon_url": "https://cdn.iconscout.com/icon/free/png-256/jira-3628861-3030001.png"},
                {"name": "AWS", "icon_url": "https://cdn.iconscout.com/icon/free/png-256/aws-1869025-1583149.png"},
                {"name": "Google Cloud", "icon_url": "https://cdn.iconscout.com/icon/free/png-256/google-cloud-platform-2038785-1721675.png"},
                {"name": "Azure", "icon_url": "https://cdn.iconscout.com/icon/free/png-256/microsoft-azure-2038745-1721658.png"},
                {"name": "Datadog", "icon_url": "https://cdn.iconscout.com/icon/free/png-256/datadog-3628878-3029824.png"},
                {"name": "New Relic", "icon_url": "https://cdn.iconscout.com/icon/free/png-256/new-relic-3628878-3029817.png"},
                {"name": "MongoDB", "icon_url": "https://cdn.iconscout.com/icon/free/png-256/mongodb-3629020-3030245.png"},
                {"name": "PostgreSQL", "icon_url": "https://cdn.iconscout.com/icon/free/png-256/postgresql-3628899-3030131.png"},
                {"name": "MySQL", "icon_url": "https://cdn.iconscout.com/icon/free/png-256/mysql-3628940-3030164.png"},
                {"name": "Docker", "icon_url": "https://cdn.iconscout.com/icon/free/png-256/docker-3629025-3030155.png"},
                {"name": "Kubernetes", "icon_url": "https://cdn.iconscout.com/icon/free/png-256/kubernets-2949129-2441984.png"}
            ]
        
        # Process the apps we got (either from API or fallback)
        processed_apps = []
        for app in all_apps:
            try:
                # Skip apps that don't have a name
                if not app.get('name'):
                    continue
                
                # Get app slug from slug or generate from name
                app_slug = app.get('slug', '').lower() or app.get('name', '').lower().replace(' ', '-')
                
                # Create AppInfo object with proper error handling
                app_info = {
                    "name": app.get('name', ''),
                    "slug": app_slug,
                    "description": app.get('description', ''),
                    "icon_url": app.get('icon_url') or app.get('logo_url') or app.get('img_src', ''),
                    "category": app.get('category', 'other').lower(),
                    "is_connected": False,  # Default to not connected
                    "tools_count": 0
                }
                processed_apps.append(AppInfo(**app_info))
                
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
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error in /apps endpoint: {str(e)}", exc_info=True)
        # Fallback to basic app list without logos
        return [
            AppInfo(
                name=app_name,
                slug=app_name.lower().replace(' ', '_').replace('.', ''),
                description=f"Integration with {app_name}",
                category=app_name.lower(),  # Simple category based on name
                is_connected=False,
                tools_count=0,
                logo_url=''
            ) for app_name in MCP_APPS
        ]
