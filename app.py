import streamlit as st
from ai import analyze_problem, ai_check
from checker import is_correct

st.title("📸 Snap & Solve")
st.write("Take a picture of a math problem.")

# --- Get the photo ---
photo = st.camera_input("Snap your problem")
upload = st.file_uploader("...or upload a photo", type=["jpg", "jpeg", "png"])

image = photo or upload
if image:
    st.image(image, caption="Your problem")

# --- Send it to the AI (only when the button is clicked) ---
if image and st.button("Solve it ✨"):
    with st.spinner("Reading your problem..."):
        st.session_state.result = analyze_problem(image.getvalue(), image.type)

# --- Show the solution ---
result = st.session_state.get("result")
if result:
    if not result["is_math"]:
        st.warning("That doesn't look like a math problem. Try another photo!")
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
            if ok is None:          # SymPy couldn't read it, so ask the AI
                ok = ai_check(answer, correct)
            if ok:
                st.success("🎉 Correct! Nice work.")
            else:
                st.error("Not quite. Let's look at it another way.")