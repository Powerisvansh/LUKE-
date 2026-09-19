"""Luke Calculator — expression engine (no third-party or eval()).
Understands: + - * / ^ ( ) and trailing % (percent -> /100)."""

OPERATORS = {"+": 1, "-": 1, "*": 2, "/": 2, "^": 3}


def _fmt(value):
    if value != value:  # NaN
        raise ValueError("Result is not a number")
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    rounded = round(value, 12)
    return ("%.12g" % rounded)


def tokenize(expr):
    tokens = []
    i, n = 0, len(expr)
    while i < n:
        c = expr[i]
        if c == " ":
            i += 1
            continue
        if c.isdigit() or c == ".":
            j = i
            while j < n and (expr[j].isdigit() or expr[j] == "."):
                j += 1
            num = expr[i:j]
            try:
                val = float(num)
            except ValueError:
                raise ValueError("Invalid number")
            if j < n and expr[j] == "%":
                val /= 100.0
                j += 1
            tokens.append(("num", val))
            i = j
            continue
        if c == "(" or c == ")":
            tokens.append((c, c))
            i += 1
            continue
        if c in "+-":
            prev = tokens[-1] if tokens else None
            is_unary = prev is None or prev[0] == "op" or prev[0] == "("
            if is_unary:
                j = i + 1
                if j < n and (expr[j].isdigit() or expr[j] == "."):
                    end = j
                    while end < n and (expr[end].isdigit() or expr[end] == "."):
                        end += 1
                    val = float(expr[j:end])
                    if end < n and expr[end] == "%":
                        end += 1
                        val /= 100.0
                    if c == "-":
                        val = -val
                    tokens.append(("num", val))
                    i = end
                else:
                    tokens.append(("num", 0.0))
                    tokens.append(("op", c))
                    i += 1
            else:
                tokens.append(("op", c))
                i += 1
            continue
        if c in OPERATORS:
            tokens.append(("op", c))
            i += 1
            continue
        raise ValueError("Unsupported symbol: %s" % c)
    return tokens


def to_rpn(tokens):
    out, stack = [], []
    for kind, value in tokens:
        if kind == "num":
            out.append(("num", value))
        elif value == "(":
            stack.append(value)
        elif value == ")":
            while stack and stack[-1] != "(":
                out.append(("op", stack.pop()))
            if not stack:
                raise ValueError("Unbalanced parentheses")
            stack.pop()
        else:
            while (stack and stack[-1] != "(" and
                   OPERATORS[stack[-1]] >= OPERATORS[value]):
                out.append(("op", stack.pop()))
            stack.append(value)
    while stack:
        if stack[-1] == "(":
            raise ValueError("Unbalanced parentheses")
        out.append(("op", stack.pop()))
    return out


def _apply(op, a, b):
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    if op == "^":
        try:
            result = a ** b
        except (OverflowError, ZeroDivisionError):
            raise ValueError("Result too large")
        if result != result or abs(result) > 1e308:
            raise ValueError("Result too large")
        return result
    raise ValueError("Unknown operator: %s" % op)


def evaluate(expr):
    tokens = tokenize(expr)
    if not tokens:
        raise ValueError("Nothing to calculate")
    rpn = to_rpn(tokens)
    stack = []
    for kind, value in rpn:
        if kind == "num":
            stack.append(value)
        else:
            if len(stack) < 2:
                raise ValueError("Incomplete expression")
            b = stack.pop()
            a = stack.pop()
            stack.append(_apply(value, a, b))
    if len(stack) != 1:
        raise ValueError("Incomplete expression")
    return _fmt(stack[0])


def negate_trailing(expr):
    """Flip the sign of the number at the end of the expression."""
    if not expr:
        return "-"
    j = len(expr)
    while j > 0 and (expr[j - 1].isdigit() or expr[j - 1] == "."):
        j -= 1
    if j == len(expr):
        return expr  # nothing numeric at the end
    num = expr[j:]
    prefix = expr[:j]
    if prefix == "-":
        return num
    if prefix.endswith("+"):
        return prefix[:-1] + "-" + num
    if prefix.endswith("-"):
        return prefix[:-1] + "+" + num
    if prefix == "":
        return "-" + expr if not expr.startswith("-") else expr[1:]
    if prefix == "-":
        return num
    if prefix[-1] in "*/(^":
        if num.startswith("-"):
            return prefix + num[1:]
        return prefix + "-" + num
    return expr