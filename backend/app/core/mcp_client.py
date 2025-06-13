"""
Production-ready MCP Client for Pipedream Integration
Connects to 32+ enterprise applications via Pipedream's remote MCP server
"""

import asyncio
import aiohttp
import json
import uuid
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from contextlib import AsyncExitStack
import ssl
from urllib.parse import urljoin
import requests

# MCP SDK imports
#from mcp import ClientSession
#from mcp.client.sse import sse_client

# Load environment variables
#from dotenv import load_dotenv


class PipedreamMCPClient:
    """Simple Python client for Pipedream MCP server"""
    
    def __init__(self, 
                 client_id: str,
                 client_secret: str, 
                 project_id: str,
                 environment: str = "development",
                 external_user_id: str = "",
                 app_slug: str = "",
                 server_url: Optional[str] = None):
                 #access_token: Optional[str] = None):
        
        self.client_id = client_id
        self.client_secret = client_secret
        self.project_id = project_id
        self.environment = environment
        self.external_user_id = external_user_id
        self.app_slug = app_slug
        self.server_url = server_url or "https://remote.mcp.pipedream.net"
        self._access_token = access_token
        self._session = requests.Session()  # Reuse connection
    
    def parse_sse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Server-Sent Events response format"""
        lines = response_text.strip().split('\n')
        result = {}
        
        for line in lines:
            if line.startswith('event:'):
                result['event'] = line[6:].strip()
            elif line.startswith('data:'):
                data_str = line[5:].strip()
                try:
                    result['data'] = json.loads(data_str)
                except json.JSONDecodeError:
                    result['data'] = data_str
        
        return result
    
    
    def get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "x-pd-project-id": self.project_id,
            "x-pd-environment": self.environment,
            "x-pd-external-user-id": self.external_user_id,
            "x-pd-app-slug": self.app_slug,
            "Connection": "close",  # Don't keep connection alive
        }
    
    def initialize_session(self) -> Dict[str, Any]:
        """Initialize MCP session"""
        payload = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "pipedream-python-client",
                    "version": "1.0.0"
                }
            }
        }
        
        try:
            response = self._session.post(
                self.server_url,
                headers=self.get_headers(),
                json=payload,
                timeout=15,  # Shorter timeout
                stream=False  # Don't stream the response
            )
            
            # Parse SSE response if it's event-stream format
            if response.text.startswith('event:') or 'data:' in response.text:
                parsed_sse = self.parse_sse_response(response.text)
                response_data = parsed_sse.get('data', parsed_sse)
            else:
                try:
                    response_data = response.json() if response.text.strip() else {}
                except json.JSONDecodeError:
                    response_data = response.text
                
            return {
                "status_code": response.status_code,
                "response": response_data,
                "headers": dict(response.headers),
                "raw_text": response.text
            }
            
        except requests.Timeout:
            return {
                "status_code": 408,
                "response": "Request timed out",
                "headers": {},
                "raw_text": ""
            }
        except Exception as e:
            return {
                "status_code": 500,
                "response": f"Error: {str(e)}",
                "headers": {},
                "raw_text": ""
            }
    
    def list_tools(self) -> Dict[str, Any]:
        """List available tools from the MCP server"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        return self._make_request(payload)
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool with arguments"""
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        return self._make_request(payload)
    
    def send_message(self, content: str, role: str = "user") -> Dict[str, Any]:
        """Send a message to the MCP server - first list tools, then call appropriate one"""
        # First, let's list available tools
        tools_result = self.list_tools()
        
        if tools_result['status_code'] not in [200, 201]:
            return tools_result
        
        # Try to call a chat or message tool if available
        return self.call_tool("chat", {
            "message": {
                "role": role,
                "content": content
            }
        })
    
    def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to the MCP server with error handling"""
        try:
            response = self._session.post(
                self.server_url,
                headers=self.get_headers(),
                json=payload,
                timeout=15,
                stream=False
            )
            
            # Parse SSE response if it's event-stream format  
            if response.text.startswith('event:') or 'data:' in response.text:
                parsed_sse = self.parse_sse_response(response.text)
                response_data = parsed_sse.get('data', parsed_sse)
            else:
                try:
                    response_data = response.json() if response.text.strip() else {}
                except json.JSONDecodeError:
                    response_data = response.text
                
            return {
                "status_code": response.status_code,
                "response": response_data,
                "headers": dict(response.headers),
                "raw_text": response.text
            }
            
        except requests.Timeout:
            return {
                "status_code": 408,
                "response": "Request timed out after 15 seconds",
                "headers": {},
                "raw_text": ""
            }
        except requests.ConnectionError as e:
            return {
                "status_code": 500,
                "response": f"Connection error: {str(e)}",
                "headers": {},
                "raw_text": ""
            }
        except Exception as e:
            return {
                "status_code": 500,
                "response": f"Unexpected error: {str(e)}",
                "headers": {},
                "raw_text": ""
            }


# Factory function for easy initialization
def create_pipedream_client(**kwargs) -> PipedreamMCPClient:
    """Create a Pipedream MCP client with environment variables as defaults"""
    
    # You'll need to define these variables or pass them in kwargs
    config = {
        "client_id": kwargs.get("client_id", "your_client_id"),
        "client_secret": kwargs.get("client_secret", "your_client_secret"),
        "project_id": kwargs.get("project_id", "your_project_id"),
        "environment": kwargs.get("environment", "development"),
        "external_user_id": kwargs.get("external_user_id", "vishnnu"),
        "app_slug": kwargs.get("app_slug", "asana"),
        "server_url": kwargs.get("server_url", "https://remote.mcp.pipedream.net"),
    }
    
    return PipedreamMCPClient(**config)