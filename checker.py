from sympy import python, simplify
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor,
)

TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)

def _values(answer):
    """Turn 'x = 2, x = -3' or '4' or '8/2' into a list of SymPy values."""
    values = []
    for part in answer.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            part = part.split("=")[-1]   # keep the right side of x = 4
        values.append(parse_expr(part, transformations=TRANSFORMS))
    return values

def is_correct(student, correct):
    """True, False, or None when SymPy can't read the student's answer."""
    try:
        s, c = _values(student), _values(correct)
    except Exception:
        return None
    if not s or len(s) != len(c):
        return False
    return all(any(simplify(a - b) == 0 for b in c) for a in s)
