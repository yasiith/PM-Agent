import os
import aiohttp
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class JiraMCPClient:
    def __init__(self):
        # MCP server configuration from environment variables
        self.mcp_server_url = os.getenv("MCP_SERVER_URL")
        self.jira_instance = os.getenv("JIRA_INSTANCE")
        self.api_key = os.getenv("JIRA_API_KEY")
        
        if not self.mcp_server_url:
            raise ValueError("MCP_SERVER_URL environment variable not set")
        if not self.api_key:
            raise ValueError("JIRA_API_KEY environment variable not set")
        
        # Session for making HTTP requests
        self.session = None
    
    async def _ensure_session(self):
        """Ensure an aiohttp session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            })
        return self.session
    
    async def _send_mcp_request(self, endpoint: str, method: str, params: Dict[str, Any] = None) -> Any:
        """
        Send a request to the MCP server
        
        Args:
            endpoint: The MCP endpoint (e.g., "jira")
            method: The method to call (e.g., "getIssues")
            params: Parameters to send with the request
            
        Returns:
            The response from the MCP server
        """
        session = await self._ensure_session()
        
        url = f"{self.mcp_server_url}/{endpoint}/{method}"
        
        try:
            async with session.post(url, json=params or {}) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"MCP server returned error {response.status}: {error_text}")
                
                return await response.json()
        except aiohttp.ClientError as e:
            raise Exception(f"Error communicating with MCP server: {str(e)}")
    
    async def get_issues(self, issue_type: str, status: str) -> List[Dict[str, Any]]:
        """
        Get issues from Jira via MCP server
        
        Args:
            issue_type: The type of issue (bug, task, story, etc.)
            status: The status of issues to retrieve (open, closed, all)
            
        Returns:
            List of issues matching the criteria
        """
        params = {
            "instance": self.jira_instance,
            "type": issue_type,
            "status": status
        }
        
        response = await self._send_mcp_request("jira", "getIssues", params)
        return response.get("issues", [])
    
    async def create_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new issue in Jira via MCP server"""
        params = {
            "instance": self.jira_instance,
            **issue_data
        }
        
        response = await self._send_mcp_request("jira", "createIssue", params)
        return response
    
    async def update_issue(self, issue_key: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing issue in Jira via MCP server"""
        params = {
            "instance": self.jira_instance,
            "key": issue_key,
            **update_data
        }
        
        response = await self._send_mcp_request("jira", "updateIssue", params)
        return response
    
    async def search_issues(self, jql: str) -> List[Dict[str, Any]]:
        """
        Search for issues using JQL (Jira Query Language)
        
        Args:
            jql: The JQL query string
            
        Returns:
            List of issues matching the query
        """
        params = {
            "instance": self.jira_instance,
            "jql": jql
        }
        
        response = await self._send_mcp_request("jira", "searchIssues", params)
        return response.get("issues", [])
    
    async def get_issue_details(self, issue_key: str) -> Dict[str, Any]:
        """Get detailed information about a specific issue"""
        params = {
            "instance": self.jira_instance,
            "key": issue_key
        }
        
        response = await self._send_mcp_request("jira", "getIssueDetails", params)
        return response
    
    async def close(self):
        """Close the client session"""
        if self.session and not self.session.closed:
            await self.session.close()