import uuid
import streamlit as st
from dotenv import load_dotenv

load_dotenv(".envrc")

# Import RAG pipeline directly — no Flask needed
from movie_assistant.rag import rag
from movie_assistant.db import save_conversation, save_feedback
from movie_assistant.db_prep import init_db

# Initialize DB schema on startup
init_db()

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
                result = rag(question, model=model, prompt_version=prompt_version)
                conversation_id = str(uuid.uuid4())
                data = result.model_dump()
                data["response_time"] = 0.0
                save_conversation(conversation_id, question, data)

                st.success(result.answer)
                st.caption(
                    f"Model: `{result.model}` | "
                    f"Prompt: `{result.prompt_version}` | "
                    f"Relevance: `{result.relevance}`"
                )
                st.session_state.conversation_id = conversation_id

            except Exception as e:
                st.error(f"Error: {e}")

if "conversation_id" in st.session_state:
    st.divider()
    st.write("Was this answer helpful?")
    fb_col1, fb_col2 = st.columns(2)
    with fb_col1:
        if st.button("👍 Yes"):
            save_feedback(st.session_state.conversation_id, 1)
            st.success("Thanks!")
    with fb_col2:
        if st.button("👎 No"):
            save_feedback(st.session_state.conversation_id, -1)
            st.success("Thanks for the feedback!")
