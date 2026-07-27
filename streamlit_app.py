import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv(".envrc")

API_URL = os.getenv("API_URL", "http://localhost:5000")

st.title("Movie Assistant")
st.caption("Ask me anything about movies — recommendations, genres, directors, vibes.")

question = st.text_input("Your question:", placeholder="e.g. mind-bending sci-fi like Inception")

col_model, col_prompt = st.columns(2)
with col_model:
    model = st.selectbox("Model", ["gpt-5.6-luna", "gpt-5.4-mini"])
with col_prompt:
    prompt_version = st.selectbox("Prompt", ["b", "a"], help="B = friendly assistant, A = film critic")

if st.button("Ask", type="primary"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Thinking..."):
            try:
                resp = requests.post(
                    f"{API_URL}/question",
                    json={"question": question, "model": model, "prompt_version": prompt_version},
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json()

                st.success(data["answer"])

                st.caption(
                    f"Model: `{data['model']}` | "
                    f"Prompt: `{data.get('prompt_version','?')}` | "
                    f"Relevance: `{data['relevance']}`"
                )

                st.session_state.conversation_id = data["conversation_id"]

            except Exception as e:
                st.error(f"Error: {e}")

# Feedback buttons — always visible after a response
if "conversation_id" in st.session_state:
    st.divider()
    st.write("Was this answer helpful?")
    fb_col1, fb_col2 = st.columns(2)
    with fb_col1:
        if st.button("👍 Yes"):
            requests.post(
                f"{API_URL}/feedback",
                json={"conversation_id": st.session_state.conversation_id, "feedback": 1},
            )
            st.success("Thanks!")
    with fb_col2:
        if st.button("👎 No"):
            requests.post(
                f"{API_URL}/feedback",
                json={"conversation_id": st.session_state.conversation_id, "feedback": -1},
            )
            st.success("Thanks for the feedback!")
