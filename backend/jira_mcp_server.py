import os
import json
import base64
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Get Jira credentials from environment
JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

if not all([JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY]):
    raise ValueError("Missing Jira environment variables")

# Create authentication header
auth_str = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
AUTH_HEADER = base64.b64encode(auth_str.encode()).decode()

app = FastAPI()

@app.post("/jira/getIssues")
async def get_issues(request: Request):
    """MCP endpoint to get issues from Jira"""
    data = await request.json()
    instance = data.get("instance", "default")
    issue_type = data.get("type", "all")
    status = data.get("status", "all")
    
    # Build JQL query
    jql = f"project = {JIRA_PROJECT_KEY}"
    if issue_type.lower() != "all":
        jql += f" AND issuetype = '{issue_type}'"
    if status.lower() != "all" and status.lower() != "open":
        jql += f" AND status = '{status}'"
    elif status.lower() == "open":
        jql += f" AND status != 'Done' AND status != 'Closed'"
    
    # Call Jira API
    response = requests.get(
        f"{JIRA_URL}/rest/api/3/search",
        headers={
            "Authorization": f"Basic {AUTH_HEADER}",
            "Content-Type": "application/json"
        },
        params={
            "jql": jql,
            "fields": "summary,status,assignee,priority,issuetype,description"
        }
    )
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    # Process the response into a simplified format
    jira_data = response.json()
    issues = []
    
    for issue in jira_data.get("issues", []):
        issues.append({
            "key": issue["key"],
            "summary": issue["fields"]["summary"],
            "status": issue["fields"]["status"]["name"],
            "assignee": issue["fields"].get("assignee", {}).get("displayName", "Unassigned"),
            "priority": issue["fields"].get("priority", {}).get("name", "None"),
            "type": issue["fields"]["issuetype"]["name"]
        })
    
    return {"issues": issues}

@app.post("/jira/createIssue")
async def create_issue(request: Request):
    """MCP endpoint to create a Jira issue"""
    data = await request.json()
    instance = data.get("instance", "default")
    
    # Prepare issue data
    issue_data = {
        "fields": {
            "project": {
                "key": JIRA_PROJECT_KEY
            },
            "summary": data.get("summary", "New Issue"),
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": data.get("description", "")
                            }
                        ]
                    }
                ]
            },
            "issuetype": {
                "name": data.get("type", "Task")
            }
        }
    }
    
    # Call Jira API
    response = requests.post(
        f"{JIRA_URL}/rest/api/3/issue",
        headers={
            "Authorization": f"Basic {AUTH_HEADER}",
            "Content-Type": "application/json"
        },
        json=issue_data
    )
    
    if response.status_code not in (200, 201):
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    return {"key": response.json()["key"], "status": "created"}

@app.post("/jira/updateIssue")
async def update_issue(request: Request):
    """MCP endpoint to update a Jira issue"""
    data = await request.json()
    issue_key = data.get("key")
    
    if not issue_key:
        raise HTTPException(status_code=400, detail="Issue key is required")
    
    # Remove non-field data
    update_fields = {k: v for k, v in data.items() if k not in ["instance", "key"]}
    
    # Prepare update data
    update_data = {"fields": {}}
    
    # Process common fields
    if "summary" in update_fields:
        update_data["fields"]["summary"] = update_fields["summary"]
    
    if "description" in update_fields:
        update_data["fields"]["description"] = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": update_fields["description"]
                        }
                    ]
                }
            ]
        }
    
    # Call Jira API
    response = requests.put(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}",
        headers={
            "Authorization": f"Basic {AUTH_HEADER}",
            "Content-Type": "application/json"
        },
        json=update_data
    )
    
    if response.status_code not in (200, 204):
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    return {"key": issue_key, "status": "updated"}

@app.post("/jira/searchIssues")
async def search_issues(request: Request):
    """MCP endpoint to search Jira issues using JQL"""
    data = await request.json()
    instance = data.get("instance", "default")
    jql = data.get("jql", f"project = {JIRA_PROJECT_KEY}")
    
    # Call Jira API
    response = requests.get(
        f"{JIRA_URL}/rest/api/3/search",
        headers={
            "Authorization": f"Basic {AUTH_HEADER}",
            "Content-Type": "application/json"
        },
        params={
            "jql": jql,
            "fields": "summary,status,assignee,priority,issuetype"
        }
    )
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    # Process the response
    jira_data = response.json()
    issues = []
    
    for issue in jira_data.get("issues", []):
        issues.append({
            "key": issue["key"],
            "summary": issue["fields"]["summary"],
            "status": issue["fields"]["status"]["name"],
            "assignee": issue["fields"].get("assignee", {}).get("displayName", "Unassigned"),
            "priority": issue["fields"].get("priority", {}).get("name", "None"),
            "type": issue["fields"]["issuetype"]["name"]
        })
    
    return {"issues": issues}

@app.post("/jira/getIssueDetails")
async def get_issue_details(request: Request):
    """MCP endpoint to get detailed information about a specific issue"""
    data = await request.json()
    instance = data.get("instance", "default")
    issue_key = data.get("key")
    
    if not issue_key:
        raise HTTPException(status_code=400, detail="Issue key is required")
    
    # Call Jira API
    response = requests.get(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}",
        headers={
            "Authorization": f"Basic {AUTH_HEADER}",
            "Content-Type": "application/json"
        },
        params={
            "fields": "summary,description,status,assignee,priority,issuetype,comment"
        }
    )
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    # Return the raw response for now (you can format it if needed)
    issue_data = response.json()
    
    # Format the response to match expected structure
    result = {
        "key": issue_data["key"],
        "summary": issue_data["fields"]["summary"],
        "status": issue_data["fields"]["status"]["name"],
        "assignee": issue_data["fields"].get("assignee", {}).get("displayName", "Unassigned"),
        "priority": issue_data["fields"].get("priority", {}).get("name", "None"),
        "type": issue_data["fields"]["issuetype"]["name"],
    }
    
    # Extract description
    if "description" in issue_data["fields"] and issue_data["fields"]["description"]:
        # Try to extract plain text from Atlassian Document Format
        try:
            result["description"] = issue_data["fields"]["description"]["content"][0]["content"][0]["text"]
        except (KeyError, IndexError):
            result["description"] = "Complex description format - see Jira"
    else:
        result["description"] = ""
    
    return result

if __name__ == "__main__":
    port = int(os.getenv("MCP_SERVER_PORT", "8081"))
    print(f"Starting local MCP server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)