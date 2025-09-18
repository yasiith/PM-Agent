from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from jira_mcp_client import JiraMCPClient
import openai
from dotenv import load_dotenv

app = FastAPI()
jira_client = JiraMCPClient()

class ChatMessage(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(chat_message: ChatMessage):
    try:
        user_message = chat_message.message

        # determining user intent
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """You are an AI assistant that helps with project management.
                Analyze the user's query and categorize it into one of these intents:
                - GET_OPEN_BUGS: User wants to see open bugs/issues
                - GET_TASKS: User wants to see tasks
                - CREATE_ISSUE: User wants to create a new issue (extract type and description)
                - UPDATE_ISSUE: User wants to update an existing issue (extract key and changes)
                - OTHER: User query doesn't match any of the above
                
                Respond with ONLY the intent type and any extracted parameters in JSON format.
                """},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            max_tokens=150
        )

        intent_analysis = response.choices[0].message.content

        # Process based on detected intent
        if "GET_OPEN_BUGS" in intent_analysis:
            issues = await jira_client.get_issues("bug", "open")
            return {"answer": f"Here are the open bugs: {issues}"}
        
        elif "GET_TASKS" in intent_analysis:
            issues = await jira_client.get_issues("task", "all")
            return {"answer": f"Here are the tasks: {issues}"}
        
        elif "CREATE_ISSUE" in intent_analysis:
            # Extract issue details from the intent analysis
            issue_type = "task"  
            summary = user_message
            
            new_issue = await jira_client.create_issue({
                "type": issue_type,
                "summary": summary
            })
            return {"answer": f"Created new issue: {new_issue['key']}"}
        
        elif "UPDATE_ISSUE" in intent_analysis:
            return {"answer": "Issue update functionality is coming soon"}
            
        else:
            # For queries that don't match predefined intents, use OpenAI to generate a helpful response
            general_response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a project management assistant. Respond helpfully but briefly to the user's query. If you don't have specific information, suggest what actions they could take."},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=150
            )
            return {"answer": general_response.choices[0].message.content}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

