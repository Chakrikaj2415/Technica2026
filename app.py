import streamlit as st
from ai import analyze_problem

st.title("📸 Snap & Solve")
st.write("Take a picture of a math problem.")

photo = st.camera_input("Snap your problem")
upload = st.file_uploader("...or upload a photo", type=["jpg", "jpeg", "png"])

image = photo or upload
if image:
    st.image(image, caption="Your problem")

if image and st.button("Solve it ✨"):
    with st.spinner("Reading your problem..."):
        st.session_state.result = analyze_problem(image.getvalue(), image.type)

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