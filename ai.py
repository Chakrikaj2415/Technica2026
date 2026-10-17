import json
import streamlit as st
from google import genai
from google.genai import types

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
MODEL = "gemini-2.5-flash"

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

def analyze_problem(image_bytes, mime_type="image/jpeg"):
    response = client.models.generate_content(
        model=MODEL,
        contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type), PROMPT],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return json.loads(response.text)