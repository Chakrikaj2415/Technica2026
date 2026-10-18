import random
import streamlit as st
from sympy import Eq, Poly, expand, factor, latex, solve
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor,
)

TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)

EXPLANATIONS = {
    "linear": (
        "A linear equation is like a balance scale: whatever you do to one side, "
        "you must do to the other. Your goal is to get the variable alone. "
        "First undo adding or subtracting by moving the plain numbers to the other side. "
        "Then undo multiplying by dividing by the number in front of the variable. "
        "Example: 3x + 2 = 11. Subtract 2: 3x = 9. Divide by 3: x = 3. "
        "Check it: 3(3) + 2 = 11 ✓"
    ),
    "quadratic": (
        "A quadratic equation has a squared term, like x². "
        "Step 1: move everything to one side so it equals 0. "
        "Step 2: try to factor it into two brackets, like (x − 2)(x − 3) = 0. "
        "Step 3: if two things multiply to 0, one of them must be 0, "
        "so set each bracket to 0: x = 2 or x = 3. "
        "Quadratics usually have two answers. Type both, separated by a comma: x = 2, x = 3"
    ),
}

def _parse(text):
    text = text.replace("−", "-").replace("×", "*").replace("÷", "/")
    left, right = text.split("=", 1) if "=" in text else (text, "0")
    return (parse_expr(left, transformations=TRANSFORMS),
            parse_expr(right, transformations=TRANSFORMS))

def _step(explanation, left, right):
    return {"explanation": explanation, "math": f"{latex(left)} = {latex(right)}"}

def _solve_linear(L, R, x):
    steps = [_step("Start with the equation.", L, R)]
    L, R = expand(L), expand(R)
    if steps[0]["math"] != f"{latex(L)} = {latex(R)}":
        steps.append(_step("Multiply out the parentheses on both sides.", L, R))
    a, b = Poly(L, x).coeff_monomial(x), Poly(L, x).coeff_monomial(1)
    c, d = Poly(R, x).coeff_monomial(x), Poly(R, x).coeff_monomial(1)
    if c != 0:
        verb, word = ("Subtract", "from") if c > 0 else ("Add", "to")
        a = a - c
        steps.append(_step(f"{verb} ${latex(abs(c) * x)}$ {word} both sides "
                           f"to get all the {x} terms on the left.", a * x + b, d))
    if b != 0:
        verb, word = ("Subtract", "from") if b > 0 else ("Add", "to")
        d = d - b
        steps.append(_step(f"{verb} {abs(b)} {word} both sides to get the {x} term alone.", a * x, d))
    if a != 1:
        steps.append(_step(f"Divide both sides by {a}.", x, d / a))
    return steps, f"{x} = {d / a}"

def _solve_quadratic(L, R, x):
    steps = [_step("Start with the equation.", L, R)]
    expr = expand(L - R)
    steps.append(_step("Move everything to one side so it equals 0.", expr, 0))
    sols = solve(Eq(expr, 0), x)
    factored = factor(expr)
    if factored != expr and all(s.is_rational for s in sols):
        steps.append(_step("Factor the left side.", factored, 0))
        steps.append({"explanation": "If two things multiply to 0, one of them must be 0. "
                                     "Set each factor to 0 and solve.",
                      "math": r",\quad ".join(f"{x} = {latex(s)}" for s in sols)})
    else:
        p = Poly(expr, x)
        A, B, C = p.coeff_monomial(x**2), p.coeff_monomial(x), p.coeff_monomial(1)
        steps.append({"explanation": f"It doesn't factor nicely, so use the quadratic formula "
                                     f"with a = {A}, b = {B}, c = {C}.",
                      "math": rf"{x} = \frac{{-b \pm \sqrt{{b^2 - 4ac}}}}{{2a}}"})
        steps.append({"explanation": "Plug in the numbers and simplify.",
                      "math": r",\quad ".join(f"{x} = {latex(s)}" for s in sols)})
    return steps, ", ".join(f"{x} = {s}" for s in sols)

def _practice_linear(x, easier):
    sol = random.randint(1, 6) if easier else random.choice([-1, 1]) * random.randint(1, 9)
    a = random.randint(2, 5) if easier else random.randint(2, 9)
    b = random.randint(1, 9) if easier else random.choice([-1, 1]) * random.randint(1, 15)
    return {"problem": f"Solve: ${latex(Eq(a * x + b, a * sol + b))}$",
            "answer": f"{x} = {sol}"}

def _practice_quadratic(x, easier):
    r1, r2 = random.sample(range(1, 6) if easier else range(-7, 8), 2)
    return {"problem": f"Solve: ${latex(Eq(expand((x - r1) * (x - r2)), 0))}$",
            "answer": f"{x} = {r1}, {x} = {r2}"}

@st.cache_data(show_spinner=False)
def analyze_problem(problem_text):
    try:
        L, R = _parse(problem_text)
        expr = expand(L - R)
        if len(expr.free_symbols) != 1:
            return {"is_math": False}
        x = next(iter(expr.free_symbols))
        degree = Poly(expr, x).degree()
    except Exception:
        return {"is_math": False}

    if degree == 1:
        kind, topic = "linear", "solving linear equations"
        steps, answer = _solve_linear(L, R, x)
        practice = _practice_linear
    elif degree == 2:
        kind, topic = "quadratic", "solving quadratic equations"
        steps, answer = _solve_quadratic(L, R, x)
        practice = _practice_quadratic
    else:
        return {"is_math": False}

    return {
        "is_math": True,
        "problem": problem_text,
        "topic": topic,
        "steps": steps,
        "final_answer": answer,
        "practice_1": practice(x, easier=False),
        "explanation": EXPLANATIONS[kind],
        "practice_2": practice(x, easier=True),
    }

def ai_check(student, correct):
    """No AI in this version: if SymPy can't read the answer, count it as wrong."""
    return False