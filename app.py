import re
import streamlit as st
from io import BytesIO
from urllib.parse import quote_plus
from PIL import Image
from ocrmac import ocrmac
from ai import analyze_problem, ai_check, new_practice
from checker import is_correct


# ---------- Reading the photo ----------

def _normalize(text):
    return (text.replace("−", "-").replace("–", "-").replace("×", "*").replace("÷", "/")
                .replace("²", "^2").replace("³", "^3").strip())

def _math_score(line):
    """Higher score = more likely to be a math problem."""
    if not re.search(r"[=+\-*/^]", line):          # no math operator at all → not math
        return 0
    words = re.findall(r"[A-Za-z]{2,}", line)       # real words like "Khan", "Visit"
    symbols = re.findall(r"[0-9=+\-*/^()]", line)  # numbers and math symbols
    score = len(symbols) - 3 * len(words)
    if "=" in line:
        score += 5                                  # equations are very likely problems
    return score

def read_photo(image_file):
    """Read the photo and return every line that looks like a math problem, separated by ';'."""
    img = Image.open(BytesIO(image_file.getvalue()))
    results = ocrmac.OCR(img, recognition_level="accurate").recognize()
    problems = []
    for r in results:
        line = _normalize(r[0])
        if _math_score(line) >= 3:
            line = re.sub(r"[A-Za-z]{2,}", "", line)    # drop leftover words
            line = re.sub(r"\s+", " ", line).strip()
            if line and line not in problems:
                problems.append(line)
    return " ; ".join(problems)


# ---------- Helpers ----------

def help_links(topic):
    q = quote_plus(topic)
    return {
        "Khan Academy": f"https://www.khanacademy.org/search?page_search_query={q}",
        "YouTube lessons": f"https://www.youtube.com/results?search_query={quote_plus(topic + ' math lesson')}",
    }

def show_steps(result):
    for i, step in enumerate(result["steps"], start=1):
        st.markdown(f"**Step {i}:** {step['explanation']}")
        st.latex(step["math"])


# ---------- Page ----------

st.title("📸 Snap & Solve")
st.write("Take a picture of a math problem (or a whole worksheet), check what the camera read, "
         "then solve it.")

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
    "Problem(s): check them and fix anything the camera misread. "
    "Separate multiple problems with ;",
    key="problem_text",
)

if problem_text and st.button("Solve it ✨"):
    problems = [p.strip() for p in problem_text.split(";") if p.strip()]
    st.session_state.results = [(p, analyze_problem(p)) for p in problems]

# --- Show the solutions ---
results = st.session_state.get("results", [])
if results:
    many = len(results) > 1

    if many:
        st.subheader(f"📋 Answers to all {len(results)} problems")
        for n, (p, r) in enumerate(results, start=1):
            answer = r["final_answer"] if r["is_math"] else "couldn't solve"
            st.markdown(f"**{n}.** `{p}` → **{answer}**")
        st.caption("Open each problem below to see the step-by-step solution.")

    for n, (p, result) in enumerate(results, start=1):
        title = f"Problem {n}: {p}" if many else f"Problem: {p}"
        with st.expander(title, expanded=not many):
            if not result["is_math"]:
                st.warning("I couldn't solve this one. I can do arithmetic (like 6/2(1+2)), "
                           "simplifying (like 2(x + 3) + 4x), and equations with one variable "
                           "(like 2x + 3 = 11 or x^2 - 5x + 6 = 0). Check it for typos.")
            else:
                st.markdown(f"**Topic:** {result['topic']}")
                show_steps(result)
                st.success(f"Answer: {result['final_answer']}")

    # ---------- Practice loop ----------
    solved = [r for _, r in results if r["is_math"]]
    if solved:
        first = solved[0]

        # Start fresh practice whenever a new problem is solved
        if st.session_state.get("practice_for") != first["problem"]:
            st.session_state.practice_for = first["problem"]
            st.session_state.practice = first["practice_1"]
            st.session_state.feedback = None
            st.session_state.wrong_count = 0
            st.session_state.practice_num = 1

        practice = st.session_state.practice

        st.divider()
        st.subheader(f"✏️ Your turn (practice problem {st.session_state.practice_num})")
        if many:
            st.caption(f"A practice problem on {first['topic']}:")
        st.markdown(practice["problem"])

        if st.session_state.feedback is None:
            # --- Ask for an answer ---
            with st.form(f"practice_{st.session_state.practice_num}"):
                answer = st.text_input("Your answer (for example: x = 5, or just 7)")
                submitted = st.form_submit_button("Check my answer")

            if submitted and answer.strip():
                ok = is_correct(answer, practice["answer"])
                if ok is None:                         # SymPy couldn't read the answer
                    ok = ai_check(answer, practice["answer"])
                st.session_state.last_answer = answer
                if ok:
                    st.session_state.feedback = "right"
                    st.session_state.wrong_count = 0
                else:
                    st.session_state.feedback = "wrong"
                    st.session_state.wrong_count += 1
                st.rerun()
        else:
            # --- Show feedback + the worked solution ---
            worked = analyze_problem(practice["text"])

            if st.session_state.feedback == "right":
                st.success(f"🎉 That's correct! The answer is **{practice['answer']}**. "
                           f"Here's why it works:")
            else:
                st.error(f"Not quite. You answered **{st.session_state.last_answer}**, but the "
                         f"correct answer is **{practice['answer']}**. "
                         f"Let's go through it step by step:")

            if worked["is_math"]:
                show_steps(worked)

            if st.session_state.feedback == "wrong":
                st.info(f"💡 **Tip:** {first['explanation']}")
                if st.session_state.wrong_count >= 2:
                    st.warning("This topic is tricky, and that's okay! "
                               "These lessons explain it in more depth:")
                    for name, url in help_links(first["topic"]).items():
                        st.link_button(f"📚 {name}", url)

            # --- Next problem ---
            if st.button("Try another one ➡️"):
                easier = st.session_state.feedback == "wrong"   # a bit easier after a miss
                st.session_state.practice = new_practice(first["kind"], first["var"], easier)
                st.session_state.feedback = None
                st.session_state.practice_num += 1
                st.rerun()