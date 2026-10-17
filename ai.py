import base64
import json
import streamlit as st
from openai import OpenAI

client = OpenAI(
    base_url="https://models.github.ai/inference",
    api_key=st.secrets["GITHUB_TOKEN"],
)
MODEL = "openai/gpt-4o"

PROMPT = """
You are a patient math tutor for middle and high school students.
Look at the photo of a math problem and reply with ONLY this JSON:

{
  "is_math": true or false,
  "problem": "the problem as you read it",
  "topic": "short topic name, e.g. solving two-step linear equations",
  "steps": [
    {"explanation": "one short sentence", "math": "the math for this step in LaTeX, no $ signs"}
  ],
  "final_answer": "x = 4",
  "practice_1": {"problem": "a similar problem with different numbers", "answer": "x = 7"},
  "explanation": "a simple explanation of the topic for a student who is stuck, under 120 words, with one tiny example",
  "practice_2": {"problem": "another similar problem, slightly easier", "answer": "x = 2"}
}

Rules:
- Answers must be plain math SymPy can read: numbers, variables, + - * / ^, = and parentheses. No words.
- If there are several solutions, separate them with commas: "x = 2, x = -3".
- Keep each step short. Use 3 to 8 steps.
- If the photo is not a math problem, set is_math to false and leave the other fields empty.
"""

@st.cache_data(show_spinner=False)
def analyze_problem(image_bytes, mime_type="image/jpeg"):
    b64 = base64.b64encode(image_bytes).decode()
    reply = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
        ]}],
    )
    if isinstance(reply, str):
        st.error(f"GitHub said: {reply[:500]}")
        st.stop()
    return json.loads(reply.choices[0].message.content)

def ai_check(student, correct):
    reply = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content":
            f"Is the student answer '{student}' mathematically equal to '{correct}'? Reply only yes or no."}],
    )
    return reply.choices[0].message.content.strip().lower().startswith("yes")