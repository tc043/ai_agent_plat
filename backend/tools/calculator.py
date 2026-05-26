"""
Calculator Tool Adapter.
Safe mathematical expression evaluation.
"""

import math
import re
from backend.tools import registry


SAFE_MATH_NAMES = {
    "abs": abs, "round": round, "min": min, "max": max,
    "pow": pow, "sum": sum, "len": len,
    "sqrt": math.sqrt, "log": math.log, "log10": math.log10, "log2": math.log2,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "pi": math.pi, "e": math.e, "tau": math.tau,
    "ceil": math.ceil, "floor": math.floor,
    "factorial": math.factorial, "gcd": math.gcd,
    "degrees": math.degrees, "radians": math.radians,
}


def calculate(expression: str = "") -> str:
    """Safely evaluate a mathematical expression."""
    expression_str = str(expression).strip()
    if not expression_str:
        return "Error: No expression provided."

    # Pre-process: convert '^' to '**' for exponentiation
    sanitized = expression_str.replace('^', '**')
    if re.search(r'[a-zA-Z_]\w*\s*\(', sanitized):
        # Check if all function names are in our safe list
        func_names = re.findall(r'([a-zA-Z_]\w*)\s*\(', sanitized)
        for fn in func_names:
            if fn not in SAFE_MATH_NAMES:
                return f"Error: Function '{fn}' is not allowed. Available: {', '.join(sorted(SAFE_MATH_NAMES.keys()))}"

    # Block dangerous patterns
    blocked = ["import", "exec", "eval", "open", "os.", "sys.", "__", "lambda"]
    for b in blocked:
        if b in sanitized.lower():
            return f"Error: '{b}' is not allowed in expressions."

    try:
        result = eval(sanitized, {"__builtins__": {}}, SAFE_MATH_NAMES)
        if isinstance(result, float):
            if result == int(result) and abs(result) < 1e15:
                return f"{expression_str} = {int(result)}"
            return f"{expression_str} = {result:.6g}"
        return f"{expression_str} = {result}"
    except ZeroDivisionError:
        return "Error: Division by zero."
    except Exception as e:
        return f"Error evaluating '{expression_str}': {str(e)}"


def unit_convert(value: str = "0", from_unit: str = "", to_unit: str = "") -> str:
    """Convert between common units."""
    try:
        val = float(value)
    except ValueError:
        return f"Error: '{value}' is not a valid number."

    conversions = {
        ("km", "miles"): lambda v: v * 0.621371,
        ("miles", "km"): lambda v: v / 0.621371,
        ("kg", "lbs"): lambda v: v * 2.20462,
        ("lbs", "kg"): lambda v: v / 2.20462,
        ("celsius", "fahrenheit"): lambda v: v * 9/5 + 32,
        ("fahrenheit", "celsius"): lambda v: (v - 32) * 5/9,
        ("m", "ft"): lambda v: v * 3.28084,
        ("ft", "m"): lambda v: v / 3.28084,
        ("btc", "satoshi"): lambda v: v * 100_000_000,
        ("satoshi", "btc"): lambda v: v / 100_000_000,
        ("eth", "gwei"): lambda v: v * 1_000_000_000,
        ("gwei", "eth"): lambda v: v / 1_000_000_000,
        ("eth", "wei"): lambda v: v * 1e18,
        ("wei", "eth"): lambda v: v / 1e18,
    }

    key = (from_unit.lower(), to_unit.lower())
    if key in conversions:
        result = conversions[key](val)
        return f"{val} {from_unit} = {result:,.6g} {to_unit}"

    return f"Unsupported conversion: {from_unit} → {to_unit}. Supported: {', '.join(f'{a}→{b}' for a, b in conversions.keys())}"


registry.register(
    name="calculate",
    description="Safely evaluate mathematical expressions. Supports basic arithmetic, trigonometry, logarithms, and common math functions.",
    category="math",
    parameters=[
        {"name": "expression", "type": "string", "description": "Mathematical expression to evaluate (e.g., 'sqrt(144) + 2**10')"}
    ],
    examples=["Calculate 2^10", "What's sqrt(144)?", "Compute log(1000)"],
    handler=calculate,
)

registry.register(
    name="unit_convert",
    description="Convert between units including crypto units (BTC↔Satoshi, ETH↔Gwei↔Wei), distance, weight, and temperature.",
    category="math",
    parameters=[
        {"name": "value", "type": "string", "description": "Numeric value to convert"},
        {"name": "from_unit", "type": "string", "description": "Source unit"},
        {"name": "to_unit", "type": "string", "description": "Target unit"},
    ],
    examples=["Convert 1 BTC to satoshi", "Convert 100 celsius to fahrenheit"],
    handler=unit_convert,
)
