import streamlit as st
import requests
import json
import pandas as pd

st.set_page_config(page_title="AI PM Agent", page_icon="🤖", layout="centered")

# Sidebar for instructions
with st.sidebar:
    st.header("How to use")
    st.write("Ask about your project, e.g. 'Show open bugs', 'List tasks', etc.")

st.title("AI Project Management Agent 🤖")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Use callback to handle form submission and clear input
def handle_send():
    if st.session_state.user_input:
        # Store the current input value
        current_input = st.session_state.user_input
        
        with st.spinner("Thinking..."):
            try:
                response = requests.post("http://127.0.0.1:8000/chat", json={"message": current_input})
                answer = response.json()["answer"]
            except Exception as e:
                answer = f"Error: {e}"
            
            # Add to chat history
            st.session_state.chat_history.append(("user", current_input))
            st.session_state.chat_history.append(("bot", answer))
        
        # Reset the input by using the form_submit_clear key
        st.session_state.user_input = ""

# Display the text input with the key
user_input = st.text_input("Type your message:", key="user_input")

# Add a button that will send the message
send = st.button("Send", on_click=handle_send)

def display_jira_issues(data):
    """Format and display Jira issues as a table if possible"""
    try:
        # Check if data contains a list of issues
        if isinstance(data, str):
            # Try to parse if it's a string representation of list/dict
            try:
                data = eval(data)
            except:
                return data
                
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            df = pd.DataFrame(data)
            return df
        return data
    except:
        return data

# Display chat history
st.write("### Conversation")
for sender, msg in st.session_state.chat_history:
    if sender == "user":
        st.markdown(f"<div style='text-align:right; color:blue;'><b>You:</b> {msg}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='text-align:left; color:green;'><b>Agent:</b></div>", unsafe_allow_html=True)
        
        # Try to display structured data better
        formatted_data = display_jira_issues(msg)
        if isinstance(formatted_data, pd.DataFrame):
            st.dataframe(formatted_data)
        else:
            st.write(formatted_data)
