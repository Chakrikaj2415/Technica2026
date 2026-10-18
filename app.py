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
        st.subheader(f"Answers to all {len(results)} problems")
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
            st.session_state.seen = {first["practice_1"]["text"]}
            st.session_state.score = 0
            st.session_state.attempts = 0
            st.session_state.streak = 0
            st.session_state.last_drill = None

        def next_problem(easier):
            """Make a new practice problem the student hasn't seen yet."""
            for _ in range(30):
                p = new_practice(first["kind"], first["var"], easier)
                if p["text"] not in st.session_state.seen:
                    break
            st.session_state.seen.add(p["text"])
            st.session_state.practice = p
            st.session_state.feedback = None
            st.session_state.practice_num += 1

        practice = st.session_state.practice

        st.divider()
        st.subheader(f"Your turn! (practice problem {st.session_state.practice_num})")
        if many:
            st.caption(f"Practice problems on {first['topic']}:")

        drill = st.toggle("Drill mode: Practice questions until you feel ready.",
                          key="drill")
        if st.session_state.attempts:
            st.caption(f"Score: {st.session_state.score}/{st.session_state.attempts} · "
                       f"🔥 Streak: {st.session_state.streak}")

        # --- Drill mode: quick feedback on the question just answered ---
        last = st.session_state.get("last_drill")
        if drill and last:
            if last["right"]:
                st.success(f"✅ Correct! The answer was **{last['answer']}**.")
            else:
                st.error(f"❌ You answered **{last['given']}**, but the answer was "
                         f"**{last['answer']}**.")
            with st.expander("See how to solve the last one"):
                st.markdown(last["problem"])
                worked_last = analyze_problem(last["text"])
                if worked_last["is_math"]:
                    show_steps(worked_last)
            if not last["right"] and st.session_state.wrong_count >= 2:
                st.warning("This topic is tricky, and that's okay! "
                           "These lessons explain it in more depth:")
                for name, url in help_links(first["topic"]).items():
                    st.link_button(f"📚 {name}", url)

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

                st.session_state.attempts += 1
                if ok:
                    st.session_state.score += 1
                    st.session_state.streak += 1
                    st.session_state.wrong_count = 0
                else:
                    st.session_state.streak = 0
                    st.session_state.wrong_count += 1

                if drill:
                    # Remember this one for quick feedback, then go straight to a new question
                    st.session_state.last_drill = {
                        "problem": practice["problem"], "text": practice["text"],
                        "answer": practice["answer"], "given": answer, "right": ok,
                    }
                    next_problem(easier=not ok)
                else:
                    st.session_state.last_answer = answer
                    st.session_state.feedback = "right" if ok else "wrong"
                st.rerun()
        else:
            # --- Normal mode: feedback + the full worked solution ---
            worked = analyze_problem(practice["text"])

            if st.session_state.feedback == "right":
                st.success(f"That's correct! The answer is **{practice['answer']}**. "
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
            if st.button("Try another one! :)"):
                next_problem(easier=st.session_state.feedback == "wrong")
                st.rerun()


# ---------- Google search ideas (bottom of the page) ----------

SEARCH_IDEAS = {
    "arithmetic": [
        "order of operations PEMDAS explained",
        "PEMDAS multiplication and division left to right",
        "order of operations practice problems with answers",
        "why do we use the order of operations",
    ],
    "simplify": [
        "how to combine like terms",
        "distributive property explained",
        "simplifying algebraic expressions practice",
        "like terms vs unlike terms examples",
    ],
    "linear": [
        "how to solve linear equations step by step",
        "solving equations with variables on both sides",
        "solving equations with fractions",
        "linear equations practice problems with answers",
    ],
    "quadratic": [
        "how to factor quadratic equations",
        "quadratic formula explained",
        "what is the discriminant in a quadratic",
        "factoring quadratics practice problems",
    ],
    "general": [
        "how to solve polynomial equations",
        "factoring cubic equations",
        "zero product property explained",
        "finding roots of polynomials step by step",
    ],
}

solved_kinds = []
for _, r in st.session_state.get("results", []):
    if r["is_math"] and (r["kind"], r["topic"]) not in solved_kinds:
        solved_kinds.append((r["kind"], r["topic"]))

if solved_kinds:
    st.divider()
    st.subheader("Want to learn more? Need more Resources? You can click on the links below.")
    for kind, topic in solved_kinds:
        if len(solved_kinds) > 1:
            st.caption(f"For {topic}:")
        for idea in SEARCH_IDEAS.get(kind, []):
            st.link_button(f"{idea}", "https://www.google.com/search?q=" + quote_plus(idea))