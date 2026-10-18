import random
import re
from math import gcd
import streamlit as st
from sympy import Eq, Poly, Rational, Symbol, expand, factor, latex, simplify, solve
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor,
)

TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)

EXPLANATIONS = {
    "arithmetic": (
        "Use the order of operations, often remembered as PEMDAS: Parentheses first, "
        "then Exponents, then Multiplication and Division from left to right, "
        "then Addition and Subtraction from left to right. "
        "Multiplication does NOT always come before division, and addition does NOT always "
        "come before subtraction: whichever comes first reading left to right goes first. "
        "Example: 8 ÷ 2 × 4 = 4 × 4 = 16, and 10 − 3 + 2 = 7 + 2 = 9."
    ),
    "simplify": (
        "To simplify, multiply out any parentheses, then combine like terms: terms with "
        "the same variable and power. Think of x as an apple: 3 apples + 2 apples = 5 apples, "
        "so 3x + 2x = 5x. Plain numbers combine with plain numbers. You can't combine x with x², "
        "just like apples and bananas. Example: 2(x + 3) + 4x = 2x + 6 + 4x = 6x + 6."
    ),
    "linear": (
        "A linear equation is like a balance scale: whatever you do to one side, "
        "you must do to the other. Your goal is to get the variable alone. "
        "First undo adding or subtracting by moving the plain numbers to the other side. "
        "Then undo multiplying by dividing by the number in front of the variable "
        "(or multiplying by its flip if it's a fraction). "
        "Example: 3x + 2 = 11. Subtract 2: 3x = 9. Divide by 3: x = 3. Check: 3(3) + 2 = 11 ✓"
    ),
    "quadratic": (
        "A quadratic equation has a squared term, like x². "
        "Step 1: move everything to one side so it equals 0. "
        "Step 2: try to factor it into two brackets, like (x − 2)(x − 3) = 0. "
        "Step 3: if two things multiply to 0, one of them must be 0, "
        "so set each bracket to 0: x = 2 or x = 3. "
        "Quadratics usually have two answers. Type both, separated by a comma: x = 2, x = 3"
    ),
    "general": (
        "To solve an equation with higher powers, move everything to one side so it equals 0, "
        "then try to factor it into smaller pieces. If several things multiply to 0, at least "
        "one of them must be 0, so set each factor equal to 0 and solve each small equation. "
        "Example: x³ − x = 0 → x(x − 1)(x + 1) = 0 → x = 0, 1, or −1. "
        "Type all answers separated by commas."
    ),
}

# ---------- helpers ----------

def _clean(text):
    text = (text.replace("−", "-").replace("–", "-").replace("×", "*").replace("÷", "/")
                .replace("²", "^2").replace("³", "^3").strip())
    text = re.sub(r"[\s=+\-*/^]*\?+\s*$", "", text)   # drop "= ?", "-?", "?" at the end
    text = re.sub(r"[\s=+\-*/^]+$", "", text)         # drop any leftover symbol at the end
    return text.replace("?", "").strip()

def _p(text, evaluate=True):
    return parse_expr(text, transformations=TRANSFORMS, evaluate=evaluate)

def _tex(text):
    """Show math exactly the way it was typed, without simplifying it."""
    try:
        return latex(_p(text, evaluate=False))
    except Exception:
        return text

def _pn(v):
    """LaTeX for a number, wrapped in parentheses if it's negative."""
    s = latex(v)
    return f"\\left({s}\\right)" if v.is_negative else s

def _pretty(text):
    return text.replace("*", " × ").replace("/", " ÷ ")

def _step(explanation, left, right):
    return {"explanation": explanation, "math": f"{latex(left)} = {latex(right)}"}

def _solutions(x, sols):
    return r",\quad ".join(f"{x} = {latex(s)}" for s in sols), ", ".join(f"{x} = {s}" for s in sols)

def _check(L, R, x, sols):
    parts, maths = [], []
    for s in sols:
        lv, rv = simplify(L.subs(x, s)), simplify(R.subs(x, s))
        mark = "✓" if simplify(lv - rv) == 0 else "✗"
        parts.append(f"with ${x} = {latex(s)}$, the left side is ${latex(lv)}$ "
                     f"and the right side is ${latex(rv)}$ {mark}")
        maths.append(f"{x} = {latex(s)}")
    return {"explanation": "Check the answer by putting it back into the problem: "
                           + "; ".join(parts)
                           + ". Both sides match, so the answer is correct!",
            "math": r",\quad ".join(maths)}

def _start(left_text, right_text, L, R, x):
    """Step 1 shows the problem as typed. If anything gets simplified, explain exactly what."""
    original = f"{_tex(left_text)} = {_tex(right_text)}"
    steps = [{"explanation": f"Here is the problem, written exactly as you typed it. "
                             f"Our goal is to find the value of {x} that makes the left side "
                             f"equal the right side.",
              "math": original}]
    simplified = f"{latex(L)} = {latex(R)}"
    if simplified != original:
        reduced = []
        for n, d in re.findall(r"(\d+)\s*/\s*(\d+)", f"{left_text} {right_text}"):
            n, d = int(n), int(d)
            if n != 0 and d != 0 and gcd(n, d) > 1:
                g = gcd(n, d)
                reduced.append(f"{n}/{d}: both numbers can be divided by {g}, so "
                               f"{n} ÷ {g} = {n // g} and {d} ÷ {g} = {d // g}, giving {Rational(n, d)}")
        if reduced:
            why = ("First, make the numbers simpler by reducing the fractions to lowest terms. "
                   + "; ".join(reduced)
                   + ". This doesn't change their value. It just makes them easier to work with.")
        else:
            why = ("First, tidy up each side: combine any like terms "
                   f"({x} terms with {x} terms, plain numbers with plain numbers). "
                   "The value doesn't change. It just looks simpler.")
        steps.append({"explanation": why, "math": simplified})
    return steps

def _result(text, topic, steps, answer, kind, practice, x):
    return {
        "is_math": True,
        "problem": text,
        "topic": topic,
        "kind": kind,
        "var": str(x) if x is not None else None,
        "steps": steps,
        "final_answer": answer,
        "practice_1": practice(x, easier=False),
        "explanation": EXPLANATIONS[kind],
        "practice_2": practice(x, easier=True),
    }

# ---------- arithmetic, one operation at a time ----------

def _tokens(work):
    """Split something like '22-11+2' or '6/2[3]' into numbers and operators."""
    work = work.replace(" ", "")
    raw = re.findall(r"\d+\.\d+|\d+|\[[^\]]*\]|[+\-*/^]", work)
    if "".join(raw) != work:
        return None
    toks, neg = [], False
    for t in raw:
        if t in ("+", "-", "*", "/", "^"):
            if t == "-" and (not toks or isinstance(toks[-1], str)):
                neg = not neg                      # a negative sign, like -5
                continue
            if not toks or isinstance(toks[-1], str):
                return None
            toks.append(t)
        else:
            val = _p(t[1:-1] if t.startswith("[") else t)
            if neg:
                val, neg = -val, False
            if toks and not isinstance(toks[-1], str):
                toks.append("*")                   # 2(3) means 2 × 3
            toks.append(val)
    if not toks or isinstance(toks[-1], str):
        return None
    return toks

def _show(toks):
    out = []
    for t in toks:
        if isinstance(t, str):
            out.append({"*": r"\times", "/": r"\div"}.get(t, t))
        elif t.is_integer and t >= 0:
            out.append(latex(t))
        else:
            out.append(f"\\left({latex(t)}\\right)")
    return " ".join(out)

def _pemdas_steps(toks):
    steps = []
    rounds = [
        (("^",), "Exponents come next"),
        (("*", "/"), "Next, do multiplication and division, working from left to right"),
        (("+", "-"), "Finally, do addition and subtraction, working from left to right"),
    ]
    for ops, intro in rounds:
        i = 1
        while i < len(toks):
            if isinstance(toks[i], str) and toks[i] in ops:
                a, op, b = toks[i - 1], toks[i], toks[i + 1]
                if op == "^":
                    val = a ** b
                elif op == "*":
                    val = a * b
                elif op == "/":
                    val = a / b
                elif op == "+":
                    val = a + b
                else:
                    val = a - b
                toks = toks[:i - 1] + [val] + toks[i + 2:]
                steps.append({"explanation": f"{intro}. Work out ${_show([a, op, b])} = {latex(val)}$. "
                                             f"Now the problem looks like this:",
                              "math": _show(toks)})
            else:
                i += 2
    return steps, toks[0]

def _evaluate_arithmetic(text):
    steps = [{"explanation": "Here is the problem. We'll solve it using the order of operations "
                             "(PEMDAS): Parentheses first, then Exponents, then Multiplication and "
                             "Division from left to right, then Addition and Subtraction from "
                             "left to right.",
              "math": _tex(text)}]
    work = text
    while True:
        m = re.search(r"\(([^()]*)\)", work)          # innermost parentheses
        if not m:
            break
        inner = m.group(1).replace("[", "(").replace("]", ")")
        value = _p(inner)
        work = work[:m.start()] + f"[{value}]" + work[m.end():]
        if inner.strip() != str(value):
            shown = work.replace("[", "(").replace("]", ")")
            steps.append({"explanation": f"Parentheses come first. Work out what's inside them: "
                                         f"{_pretty(inner.strip())} = {value}. "
                                         f"Now the problem looks like this:",
                          "math": _tex(shown)})

    toks = _tokens(work)
    if toks:
        more, total = _pemdas_steps(toks)
        steps += more
        if not more:
            steps.append({"explanation": "That's the final answer:", "math": latex(total)})
    else:                                              # fallback for anything unusual
        shown = work.replace("[", "(").replace("]", ")")
        total = _p(shown)
        steps.append({"explanation": "Now do any exponents, then multiplication and division "
                                     "from left to right, and finally addition and subtraction "
                                     "from left to right:",
                      "math": f"{_tex(shown)} = {latex(total)}"})
    return steps, str(total)

# ---------- algebra ----------

def _simplify(text, L, x):
    steps = [{"explanation": f"Here is the expression as you typed it. There's no equals sign, "
                             f"so our goal is to simplify it (write it in its shortest, neatest "
                             f"form), not to solve for {x}.",
              "math": _tex(text)}]
    expanded = expand(L)
    steps.append({"explanation": f"Multiply out any parentheses by distributing: multiply the "
                                 f"number in front by every term inside. Then combine like terms: "
                                 f"add the {x} terms together, and add the plain numbers together.",
                  "math": latex(expanded)})
    factored = factor(expanded)
    if factored != expanded:
        steps.append({"explanation": "This can also be written in factored form, which means as "
                                     "pieces multiplied together. Both forms are equal:",
                      "math": latex(factored)})
    return steps, str(expanded)

def _solve_linear(L, R, x, left_text, right_text):
    steps = _start(left_text, right_text, L, R, x)
    EL, ER = expand(L), expand(R)
    if f"{latex(EL)} = {latex(ER)}" != steps[-1]["math"]:
        steps.append(_step("Get rid of the parentheses by distributing: multiply the number in "
                           "front of the parentheses by every term inside. For example, "
                           "3(x + 2) = 3·x + 3·2 = 3x + 6. Now the equation is:", EL, ER))
    a, b = Poly(EL, x).coeff_monomial(x), Poly(EL, x).coeff_monomial(1)
    c, d = Poly(ER, x).coeff_monomial(x), Poly(ER, x).coeff_monomial(1)

    if c != 0:
        verb, word, op = ("subtract", "from", "-") if c > 0 else ("add", "to", "+")
        new_a = a - c
        steps.append(_step(
            f"There are {x} terms on both sides. To collect them on the left, {verb} "
            f"${latex(abs(c) * x)}$ {word} both sides. (Whatever you do to one side, you must do "
            f"to the other to keep the equation balanced.) "
            f"Left: ${latex(a * x)} {op} {latex(abs(c) * x)} = {latex(new_a * x)}$. "
            f"Right: the {x} term cancels out, leaving ${latex(d)}$.",
            new_a * x + b, d))
        a = new_a

    if b != 0:
        verb, word, op = ("subtract", "from", "-") if b > 0 else ("add", "to", "+")
        sign = "+" if b > 0 else "-"
        new_d = d - b
        steps.append(_step(
            f"Now get the {x} term by itself. The left side has ${sign} {latex(abs(b))}$ next to "
            f"the {x} term, so do the opposite: {verb} ${latex(abs(b))}$ {word} both sides. "
            f"Left: the ${latex(abs(b))}$ cancels out, leaving ${latex(a * x)}$. "
            f"Right: ${latex(d)} {op} {latex(abs(b))} = {latex(new_d)}$.",
            a * x, new_d))
        d = new_d

    sol = d / a
    if a != 1:
        if a.is_integer:
            steps.append(_step(
                f"Right now {x} is being multiplied by ${latex(a)}$. The opposite of multiplying "
                f"is dividing, so divide both sides by ${latex(a)}$. "
                f"Left: ${latex(a * x)} \\div {_pn(a)} = {x}$. "
                f"Right: ${latex(d)} \\div {_pn(a)} = {latex(sol)}$.",
                x, sol))
        else:
            steps.append(_step(
                f"Right now {x} is being multiplied by the fraction ${latex(a)}$. To undo that, "
                f"multiply both sides by its flip (called the reciprocal), ${latex(1 / a)}$, "
                f"because ${latex(a)} \\times {latex(1 / a)} = 1$. "
                f"Left: just {x}. Right: ${latex(d)} \\times {_pn(1 / a)} = {latex(sol)}$.",
                x, sol))

    steps.append(_check(L, R, x, [sol]))
    return steps, f"{x} = {sol}"

def _move_to_one_side(steps, L, R, expr):
    if R == 0 and latex(expr) == latex(L):
        return
    if R == 0:
        why = "Multiply out and combine like terms on the left side, so it's in standard form:"
    else:
        why = (f"Equations like this are easiest to solve when one side is 0. Subtract "
               f"${latex(R)}$ from both sides (and combine like terms) so everything is on the left:")
    steps.append(_step(why, expr, 0))

def _solve_quadratic(L, R, x, left_text, right_text):
    steps = _start(left_text, right_text, L, R, x)
    expr = expand(L - R)
    _move_to_one_side(steps, L, R, expr)
    sols = solve(Eq(expr, 0), x)
    p = Poly(expr, x)
    A, B, C = p.coeff_monomial(x**2), p.coeff_monomial(x), p.coeff_monomial(1)
    shown, answer = _solutions(x, sols)
    factored = factor(expr)

    if factored != expr and all(s.is_rational for s in sols):
        roots = sols if len(sols) == 2 else sols * 2
        if A == 1 and all(s.is_integer for s in roots):
            m, n = -roots[0], -roots[1]
            why = (f"Now factor. Look for two numbers that multiply to ${latex(C)}$ (the plain "
                   f"number) and add to ${latex(B)}$ (the number in front of {x}). Those numbers "
                   f"are ${latex(m)}$ and ${latex(n)}$, because ${_pn(m)} \\times {_pn(n)} = "
                   f"{latex(C)}$ and ${_pn(m)} + {_pn(n)} = {latex(B)}$. "
                   f"So the left side factors into two brackets:")
        else:
            why = ("Now factor the left side into simpler pieces (brackets) that multiply "
                   "together to give the original expression:")
        steps.append(_step(why, factored, 0))
        steps.append({"explanation": "If two things multiply to give 0, at least one of them must "
                                     "be 0. So set each bracket equal to 0 and solve each one "
                                     "separately. That gives:",
                      "math": shown})
    else:
        disc = B**2 - 4 * A * C
        steps.append({"explanation": f"This one doesn't factor into nice whole numbers, so use the "
                                     f"quadratic formula. It works for any equation of the form "
                                     f"$a{x}^2 + b{x} + c = 0$. Here a = {A}, b = {B}, c = {C}.",
                      "math": rf"{x} = \frac{{-b \pm \sqrt{{b^2 - 4ac}}}}{{2a}}"})
        note = " It's negative, so there are no real solutions." if disc < 0 else ""
        steps.append({"explanation": f"First work out the part under the square root (called the "
                                     f"discriminant): $b^2 - 4ac = {_pn(B)}^2 - 4 \\cdot {_pn(A)} "
                                     f"\\cdot {_pn(C)} = {latex(disc)}$.{note}",
                      "math": f"b^2 - 4ac = {latex(disc)}"})
        steps.append({"explanation": "Now plug everything into the formula and simplify. The ± "
                                     "means there are two answers: one using + and one using −.",
                      "math": shown})

    steps.append(_check(L, R, x, sols))
    return steps, answer

def _solve_general(L, R, x, left_text, right_text):
    steps = _start(left_text, right_text, L, R, x)
    expr = expand(L - R)
    _move_to_one_side(steps, L, R, expr)
    factored = factor(expr)
    if factored != expr:
        steps.append(_step("Factor it into smaller pieces that multiply together. Look for "
                           "anything every term has in common first (like a shared "
                           f"{x}), then factor what's left:", factored, 0))
    sols = solve(Eq(L, R), x)
    if not sols:
        raise ValueError("no solution found")
    shown, answer = _solutions(x, sols)
    if factored != expr:
        why = ("If several things multiply to give 0, at least one of them must be 0. "
               "Set each piece equal to 0 and solve. The solutions are:")
    else:
        why = "Solve for the values that make the equation true:"
    steps.append({"explanation": why, "math": shown})
    steps.append(_check(L, R, x, sols))
    return steps, answer

# ---------- practice problems ----------

def _practice_arithmetic(x, easier):
    a, b, c = (random.randint(2, 9) for _ in range(3))
    if easier:
        text = f"{a} + {b}"
    else:
        text = random.choice([f"{a} + {b} * {c}", f"{a * b} / {b} - {c}",
                              f"{a + b + c} - {b} + {c}", f"{c}({a} + {b})"])
    return {"text": text, "problem": f"Calculate: ${_tex(text)}$", "answer": str(_p(text))}

def _practice_simplify(x, easier):
    a, b, c = random.randint(2, 9), random.randint(2, 9), random.randint(1, 9)
    text = f"{a}{x} + {b}{x} - {c}" if easier else f"{a}({x} + {c}) - {b}{x}"
    return {"text": text, "problem": f"Simplify: ${_tex(text)}$",
            "answer": str(expand(_p(text)))}

def _practice_linear(x, easier):
    sol = random.randint(1, 6) if easier else random.choice([-1, 1]) * random.randint(1, 9)
    a = random.randint(2, 5) if easier else random.randint(2, 9)
    b = random.randint(1, 9) if easier else random.choice([-1, 1]) * random.randint(1, 15)
    sign = "+" if b > 0 else "-"
    text = f"{a}{x} {sign} {abs(b)} = {a * sol + b}"
    return {"text": text, "problem": f"Solve: ${latex(Eq(a * x + b, a * sol + b))}$",
            "answer": f"{x} = {sol}"}

def _practice_quadratic(x, easier):
    r1, r2 = random.sample(range(1, 6) if easier else range(-7, 8), 2)
    expr = expand((x - r1) * (x - r2))
    return {"text": f"{expr} = 0", "problem": f"Solve: ${latex(Eq(expr, 0))}$",
            "answer": f"{x} = {r1}, {x} = {r2}"}

_PRACTICE = {
    "arithmetic": _practice_arithmetic,
    "simplify": _practice_simplify,
    "linear": _practice_linear,
    "quadratic": _practice_quadratic,
    "general": _practice_quadratic,
}

def new_practice(kind, var, easier=False):
    """Make a fresh practice problem of the same kind (used by 'Try another one')."""
    x = Symbol(var) if var else None
    return _PRACTICE[kind](x, easier)

# ---------- main function used by app.py ----------

@st.cache_data(show_spinner=False)
def analyze_problem(problem_text):
    text = _clean(problem_text)
    left, _, right = text.partition("=")
    left, right = left.strip(), right.strip()
    try:
        L = _p(left)
        R = _p(right) if right else None
        free = L.free_symbols | (R.free_symbols if R is not None else set())

        if not free:                                   # plain arithmetic, e.g. 22-11+2
            steps, answer = _evaluate_arithmetic(left)
            return _result(text, "order of operations", steps, answer,
                           "arithmetic", _practice_arithmetic, None)
        if len(free) != 1:                             # more than one variable
            return {"is_math": False}
        x = next(iter(free))

        if R is None:                                  # no "=": simplify the expression
            steps, answer = _simplify(left, L, x)
            return _result(text, "simplifying expressions", steps, answer,
                           "simplify", _practice_simplify, x)

        expr = expand(L - R)
        degree = Poly(expr, x).degree() if expr.is_polynomial(x) else None
        if degree == 1:
            steps, answer = _solve_linear(L, R, x, left, right)
            return _result(text, "solving linear equations", steps, answer,
                           "linear", _practice_linear, x)
        if degree == 2:
            steps, answer = _solve_quadratic(L, R, x, left, right)
            return _result(text, "solving quadratic equations", steps, answer,
                           "quadratic", _practice_quadratic, x)
        steps, answer = _solve_general(L, R, x, left, right)
        return _result(text, "solving polynomial equations", steps, answer,
                       "general", _practice_quadratic, x)
    except Exception:
        return {"is_math": False}

def ai_check(student, correct):
    """No AI in this version: if SymPy can't read the answer, count it as wrong."""
    return False