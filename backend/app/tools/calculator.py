"""
AURA AI Calculator Tool
Safe mathematical expression evaluator with extensive features.
"""

import ast
import math
import operator
import statistics
from typing import Any, List, Union

from app.database.schemas import ToolResult
from app.tools.base import BaseTool


# Safe operators
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Safe math functions - expanded!
SAFE_FUNCTIONS = {
    # Basic math
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "ln": math.log,
    "abs": abs,
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
    "trunc": math.trunc,
    "factorial": math.factorial,
    "pow": pow,
    
    # Hyperbolic functions
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "asinh": math.asinh,
    "acosh": math.acosh,
    "atanh": math.atanh,
    
    # Exponential and logarithmic
    "exp": math.exp,
    "expm1": math.expm1,
    "log1p": math.log1p,
    
    # Constants
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
    "nan": math.nan,
    
    # Angle conversion
    "degrees": math.degrees,
    "radians": math.radians,
    
    # Misc
    "hypot": math.hypot,
    "copysign": math.copysign,
    "fmod": math.fmod,
    "frexp": math.frexp,
    "ldexp": math.ldexp,
    "modf": math.modf,
    "fabs": math.fabs,
    "fsum": math.fsum,
    
    # Statistics functions
    "mean": statistics.mean,
    "median": statistics.median,
    "mode": statistics.mode,
    "stdev": statistics.stdev,
    "variance": statistics.variance,
    "pstdev": statistics.pstdev,
    "pvariance": statistics.pvariance,
    "geometric_mean": statistics.geometric_mean,
    "harmonic_mean": statistics.harmonic_mean,
    "median_low": statistics.median_low,
    "median_high": statistics.median_high,
    "median_grouped": statistics.median_grouped,
    
    # Unit conversion helpers
    "to_radians": math.radians,
    "to_degrees": math.degrees,
}


class SafeEvaluator(ast.NodeVisitor):
    """AST-based safe math expression evaluator with list support."""

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node.value, str) and node.value.lower() in ("inf", "nan"):
            return float(node.value.lower())
        raise ValueError(f"Unsupported constant: {node.value}")

    def visit_List(self, node: ast.List) -> List[Union[int, float]]:
        return [self.visit(elem) for elem in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> List[Union[int, float]]:
        return [self.visit(elem) for elem in node.elts]

    def visit_Name(self, node: ast.Name) -> Any:
        name = node.id.lower()
        if name in SAFE_FUNCTIONS:
            val = SAFE_FUNCTIONS[name]
            if isinstance(val, (int, float)):
                return val
        raise ValueError(f"Unknown variable: {node.id}")

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_func = SAFE_OPERATORS[op_type]

        # Safety: prevent huge exponents
        if op_type == ast.Pow and isinstance(right, (int, float)) and abs(right) > 10000:
            raise ValueError("Exponent too large (max 10000)")

        return op_func(left, right)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        operand = self.visit(node.operand)
        return SAFE_OPERATORS[op_type](operand)

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls allowed")

        func_name = node.func.id.lower()
        if func_name not in SAFE_FUNCTIONS:
            raise ValueError(f"Unknown function: {func_name}")

        func = SAFE_FUNCTIONS[func_name]
        if not callable(func):
            raise ValueError(f"{func_name} is not a function")

        args = [self.visit(arg) for arg in node.args]
        kwargs = {}
        for kw in node.keywords:
            if kw.arg is None:
                raise ValueError("**kwargs not allowed")
            kwargs[kw.arg] = self.visit(kw.value)
        
        return func(*args, **kwargs)

    def visit_Compare(self, node: ast.Compare) -> Any:
        left = self.visit(node.left)
        for op, comp in zip(node.ops, node.comparators):
            right = self.visit(comp)
            op_type = type(op)
            if op_type == ast.Eq:
                if not (left == right):
                    return False
            elif op_type == ast.NotEq:
                if not (left != right):
                    return False
            elif op_type == ast.Lt:
                if not (left < right):
                    return False
            elif op_type == ast.LtE:
                if not (left <= right):
                    return False
            elif op_type == ast.Gt:
                if not (left > right):
                    return False
            elif op_type == ast.GtE:
                if not (left >= right):
                    return False
            else:
                raise ValueError(f"Unsupported comparison operator: {op_type.__name__}")
            left = right
        return True

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(f"Unsupported expression: {type(node).__name__}")


def safe_eval(expression: str) -> Any:
    """Safely evaluate a math expression."""
    tree = ast.parse(expression, mode="eval")
    evaluator = SafeEvaluator()
    return evaluator.visit(tree)


class CalculatorTool(BaseTool):
    """Safe mathematical expression evaluator with extensive functions."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return (
            "Evaluate mathematical expressions safely with extensive functionality. "
            "Supports: basic arithmetic, trigonometric functions (sin, cos, tan, asin, acos, atan, atan2), "
            "hyperbolic functions (sinh, cosh, tanh, asinh, acosh, atanh), logarithms (log, ln, log10, log2), "
            "exponents (exp, pow), constants (pi, e, tau, inf), statistics (mean, median, mode, stdev, variance, "
            "geometric_mean, harmonic_mean, pstdev, pvariance, median_low, median_high, median_grouped), "
            "and utility functions (sqrt, abs, round, ceil, floor, trunc, factorial, degrees, radians, hypot, "
            "copysign, fmod, frexp, ldexp, modf, fabs, fsum). Supports lists/tuples for statistical functions."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (e.g., '2 + 2', 'sqrt(16)', 'sin(pi/2)', 'mean([1,2,3])')",
                }
            },
            "required": ["expression"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        expression = kwargs.get("expression", "")
        if not expression:
            return ToolResult(success=False, error="No expression provided")

        try:
            result = safe_eval(expression)
            
            # Format the result nicely
            if isinstance(result, float) and result.is_integer():
                result_str = str(int(result))
            elif isinstance(result, list):
                result_str = ", ".join(str(x) for x in result)
            else:
                result_str = str(result)
            
            return ToolResult(
                success=True,
                output=f"🧮 Calculation Result:\n  Expression: {expression}\n  Result: {result_str}",
            )
        except (ValueError, SyntaxError, TypeError, ZeroDivisionError, statistics.StatisticsError) as e:
            return ToolResult(success=False, error=f"Calculation error: {str(e)}")
