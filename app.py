import streamlit as st
import os
from openai import OpenAI
import time

# We need to import the classify_message function from our script.
# Since it is in a folder called scripts, we can import it this way:
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
from agent_llm import classify_message

st.set_page_config(page_title="Spotify AI Agent", page_icon="🎧", layout="wide")

st.title("🎧 @SpotifyCares AI Agent")
st.markdown("A demonstration of the LLM-powered customer support agent built for the take-home assignment.")

# Setup Groq Client
api_key = os.environ.get("GROQ_API_KEY", "")
if not api_key:
    # Try reading from .env if missing in environ
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.strip().startswith("GROQ_API_KEY="):
                    api_key = line.strip().split("=", 1)[1].strip().strip("\"").strip("\'")
                    
if not api_key:
    st.warning("⚠️ GROQ_API_KEY environment variable not set. Please set it in your environment or .env file.")
    st.stop()

client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

# Sidebar for AI Metadata
with st.sidebar:
    st.header("🧠 Under the Hood")
    st.write("AI decisions for the current message will appear here.")
    metadata_container = st.empty()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Message @SpotifyCares..."):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Analyzing intent and drafting response..."):
        try:
            # Process via our core logic
            result = classify_message(client, prompt)
            
            # Extract fields
            predicted_intent = result.get("predicted_intent", "Unknown")
            predicted_escalate = result.get("predicted_escalate", False)
            escalation_reason = result.get("escalation_reason", "None")
            draft_reply = result.get("draft_reply", "Sorry, I couldn't generate a reply.")

            # Display metadata in sidebar
            with metadata_container.container():
                st.subheader("Latest Analysis")
                st.write(f"**Intent:** {predicted_intent}")
                if predicted_escalate:
                    st.error(f"**Escalate:** True\n\n**Reason:** {escalation_reason}")
                else:
                    st.success("**Escalate:** False")
                
                with st.expander("Raw JSON Response"):
                    st.json(result)

            # Display assistant response in chat message container
            with st.chat_message("assistant"):
                st.markdown(draft_reply)
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": draft_reply})

        except Exception as e:
            st.error(f"Error communicating with LLM: {str(e)}")
