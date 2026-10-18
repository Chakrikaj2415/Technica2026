import streamlit as st
from io import BytesIO
from PIL import Image
from ocrmac import ocrmac
from ai import analyze_problem, ai_check
from checker import is_correct

def read_photo(image_file):
    """Read the text in the photo using the Mac's built-in Live Text engine."""
    img = Image.open(BytesIO(image_file.getvalue()))
    results = ocrmac.OCR(img, recognition_level="accurate").recognize()
    text = " ".join(r[0] for r in results)
    return (text.replace("²", "^2").replace("³", "^3")
                .replace("×", "*").replace("÷", "/").replace("−", "-"))

st.title("📸 Snap & Solve")
st.write("Take a picture of a math problem.")

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
        st.warning("I couldn't solve that. Type one equation with one variable, "
                   "like 2x + 3 = 11 or x^2 - 5x + 6 = 0.")
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
            if ok is None:
                ok = ai_check(answer, correct)
            if ok:
                st.success("🎉 Correct! Nice work.")
            else:
                st.error("Not quite. Let's look at it another way.")