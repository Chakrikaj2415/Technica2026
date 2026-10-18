import re
import streamlit as st
from io import BytesIO
from PIL import Image
from ocrmac import ocrmac
from ai import analyze_problem, ai_check
from checker import is_correct


# ---------- Reading the photo ----------

def _normalize(text):
    return (text.replace("−", "-").replace("–", "-").replace("×", "*").replace("÷", "/")
                .replace("²", "^2").replace("³", "^3").strip())

def _math_score(line):
    """Higher score = more likely to be the math problem."""
    if not re.search(r"[=+\-*/^]", line):          # no math operator at all → not math
        return 0
    words = re.findall(r"[A-Za-z]{2,}", line)       # real words like "Khan", "Visit"
    symbols = re.findall(r"[0-9=+\-*/^()]", line)  # numbers and math symbols
    score = len(symbols) - 3 * len(words)
    if "=" in line:
        score += 5                                  # equations are very likely the problem
    return score

def read_photo(image_file):
    """Read the photo and return only the line that looks like a math problem."""
    img = Image.open(BytesIO(image_file.getvalue()))
    results = ocrmac.OCR(img, recognition_level="accurate").recognize()
    lines = [_normalize(r[0]) for r in results]
    if not lines:
        return ""
    best = max(lines, key=_math_score)
    if _math_score(best) <= 0:
        return ""
    best = re.sub(r"[A-Za-z]{2,}", "", best)        # drop any leftover words
    return re.sub(r"\s+", " ", best).strip()


# ---------- Page ----------

st.title("📸 Snap & Solve")
st.write("Take a picture of a math problem, check what the camera read, then solve it.")

# --- Get the photo ---
photo = st.camera_input("Snap your problem")
upload = st.file_uploader("...or upload a photo", type=["jpg", "jpeg", "png"])

image = photo or upload
if image:
    st.image(image, caption="Your problem")
    image_id = hash(image.getvalue())
    if st.session_state.get("last_image") != image_id:   # only read each new photo once
        st.session_state.last_image = image_id
        st.session_state.problem_text = read_photo(image)

if image and not st.session_state.get("problem_text"):
    st.info("I couldn't find a math problem in that photo. Type it in the box below.")

# --- The problem text (filled in from the photo, editable) ---
problem_text = st.text_input(
    "Problem (check it and fix anything the camera misread)",
    key="problem_text",
)

if problem_text and st.button("Solve it ✨"):
    st.session_state.result = analyze_problem(problem_text)

# --- Show the solution ---
result = st.session_state.get("result")
if result:
    if not result["is_math"]:
        st.warning("I couldn't solve that one. I can do arithmetic (like 6/2(1+2)), "
                   "simplifying (like 2(x + 3) + 4x), and equations with one variable "
                   "(like 2x + 3 = 11 or x^2 - 5x + 6 = 0). Check the problem box for typos.")
    else:
        st.subheader(f"Topic: {result['topic']}")
        for i, step in enumerate(result["steps"], start=1):
            st.markdown(f"**Step {i}:** {step['explanation']}")
            st.latex(step["math"])
        st.success(f"Answer: {result['final_answer']}")

        # --- Practice problem 1 ---
        st.divider()
        st.subheader("✏️ Your turn")
        st.markdown(result["practice_1"]["problem"])

        with st.form("practice_1"):
            answer = st.text_input("Your answer (for example: x = 5)")
            submitted = st.form_submit_button("Check my answer")

        if submitted and answer.strip():
            correct = result["practice_1"]["answer"]
            ok = is_correct(answer, correct)
            if ok is None:                 # SymPy couldn't read the answer
                ok = ai_check(answer, correct)
            if ok:
                st.success("🎉 Correct! Nice work.")
            else:
                st.error("Not quite. Let's look at it another way.")