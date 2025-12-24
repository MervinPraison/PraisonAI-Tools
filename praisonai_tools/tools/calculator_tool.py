"""Calculator Tool for PraisonAI Agents.

Perform mathematical calculations.

Usage:
    from praisonai_tools import CalculatorTool
    
    calc = CalculatorTool()
    result = calc.add(5, 3)
    result = calc.evaluate("2 * (3 + 4)")
"""

import math
import logging
from typing import Any, Dict, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class CalculatorTool(BaseTool):
    """Tool for mathematical calculations."""
    
    name = "calculator"
    description = "Perform mathematical calculations."
    
    def __init__(self):
        super().__init__()
    
    def run(
        self,
        action: str = "evaluate",
        expression: str = None,
        a: float = None,
        b: float = None,
        n: int = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        action = action.lower().replace("-", "_")
        
        if action == "evaluate":
            return self.evaluate(expression=expression)
        elif action == "add":
            return self.add(a=a, b=b)
        elif action == "subtract":
            return self.subtract(a=a, b=b)
        elif action == "multiply":
            return self.multiply(a=a, b=b)
        elif action == "divide":
            return self.divide(a=a, b=b)
        elif action == "power":
            return self.power(a=a, b=b)
        elif action == "sqrt":
            return self.sqrt(n=a or n)
        elif action == "factorial":
            return self.factorial(n=n)
        elif action == "is_prime":
            return self.is_prime(n=n)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def evaluate(self, expression: str) -> Dict[str, Any]:
        """Evaluate a mathematical expression safely."""
        if not expression:
            return {"error": "expression is required"}
        
        try:
            allowed_names = {
                "abs": abs, "round": round, "min": min, "max": max,
                "sum": sum, "pow": pow, "len": len,
                "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
                "exp": math.exp, "pi": math.pi, "e": math.e,
                "floor": math.floor, "ceil": math.ceil,
            }
            
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return {"expression": expression, "result": result}
        except Exception as e:
            logger.error(f"Calculator evaluate error: {e}")
            return {"error": str(e)}
    
    def add(self, a: float, b: float) -> Dict[str, Any]:
        """Add two numbers."""
        if a is None or b is None:
            return {"error": "a and b are required"}
        return {"operation": "add", "a": a, "b": b, "result": a + b}
    
    def subtract(self, a: float, b: float) -> Dict[str, Any]:
        """Subtract b from a."""
        if a is None or b is None:
            return {"error": "a and b are required"}
        return {"operation": "subtract", "a": a, "b": b, "result": a - b}
    
    def multiply(self, a: float, b: float) -> Dict[str, Any]:
        """Multiply two numbers."""
        if a is None or b is None:
            return {"error": "a and b are required"}
        return {"operation": "multiply", "a": a, "b": b, "result": a * b}
    
    def divide(self, a: float, b: float) -> Dict[str, Any]:
        """Divide a by b."""
        if a is None or b is None:
            return {"error": "a and b are required"}
        if b == 0:
            return {"error": "Division by zero"}
        return {"operation": "divide", "a": a, "b": b, "result": a / b}
    
    def power(self, a: float, b: float) -> Dict[str, Any]:
        """Raise a to power b."""
        if a is None or b is None:
            return {"error": "a and b are required"}
        return {"operation": "power", "a": a, "b": b, "result": math.pow(a, b)}
    
    def sqrt(self, n: float) -> Dict[str, Any]:
        """Square root."""
        if n is None:
            return {"error": "n is required"}
        if n < 0:
            return {"error": "Cannot compute square root of negative number"}
        return {"operation": "sqrt", "n": n, "result": math.sqrt(n)}
    
    def factorial(self, n: int) -> Dict[str, Any]:
        """Factorial of n."""
        if n is None:
            return {"error": "n is required"}
        if n < 0:
            return {"error": "Factorial undefined for negative numbers"}
        return {"operation": "factorial", "n": n, "result": math.factorial(int(n))}
    
    def is_prime(self, n: int) -> Dict[str, Any]:
        """Check if n is prime."""
        if n is None:
            return {"error": "n is required"}
        n = int(n)
        if n <= 1:
            return {"n": n, "is_prime": False}
        for i in range(2, int(math.sqrt(n)) + 1):
            if n % i == 0:
                return {"n": n, "is_prime": False}
        return {"n": n, "is_prime": True}


def calculate(expression: str) -> Dict[str, Any]:
    """Evaluate mathematical expression."""
    return CalculatorTool().evaluate(expression=expression)
