from __future__ import annotations


def unescape_literal(literal: str) -> str:
    """Decode a Spark SQL single-quoted literal following Spark 4.0 rules.

    Covers only the backslash escapes the builder emits (backslash and quote); it does not
    model other Spark escapes such as unicode, octal or newline sequences.
    """
    assert literal[0] == literal[-1] == "'"
    body, out, i = literal[1:-1], [], 0
    while i < len(body):
        ch = body[i]
        if ch == "\\":
            out.append(body[i + 1])
            i += 2
        else:
            assert ch != "'", "unescaped quote inside literal"
            out.append(ch)
            i += 1
    return "".join(out)
