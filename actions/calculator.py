import ast
import operator


_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def calculate_expression(expression: str):
    if not expression or not expression.strip():
        raise ValueError("No calculation provided.")

    parsed = ast.parse(expression.strip(), mode="eval")
    return _evaluate(parsed.body)


def _evaluate(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.Num):
        return node.n

    if isinstance(node, ast.BinOp):
        operator_type = type(node.op)
        if operator_type not in _OPERATORS:
            raise ValueError("Unsupported operator.")
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        return _OPERATORS[operator_type](left, right)

    if isinstance(node, ast.UnaryOp):
        operator_type = type(node.op)
        if operator_type not in _OPERATORS:
            raise ValueError("Unsupported operator.")
        return _OPERATORS[operator_type](_evaluate(node.operand))

    raise ValueError("Unsupported expression.")
