import re
import sys


def convert_to_markdown(text: str) -> str:
    pattern = re.compile(r"\[R(\d+)-C(\d+)\s*//\s*(.*?)\]")
    cells = pattern.findall(text)
    if not cells:
        return text.strip()

    table = {}
    max_row = 0
    max_col = 0
    for r, c, val in cells:
        r = int(r)
        c = int(c)
        max_row = max(max_row, r)
        max_col = max(max_col, c)
        table.setdefault(r, {})[c] = val.strip()

    lines = []
    header = [table.get(1, {}).get(c, '') for c in range(1, max_col + 1)]
    lines.append('| ' + ' | '.join(header) + ' |')
    lines.append('|' + '|'.join(['---'] * max_col) + '|')
    for row in range(2, max_row + 1):
        line = '| ' + ' | '.join(table.get(row, {}).get(c, '') for c in range(1, max_col + 1)) + ' |'
        lines.append(line)
    return '\n'.join(lines)


if __name__ == '__main__':
    input_text = sys.stdin.read()
    print(convert_to_markdown(input_text))
