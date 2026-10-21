#!/usr/bin/env python3
"""명세서 폴더의 md 마다 같은 이름의 읽기 전용 html 을 만든다.

사용법: to_html.py <.requirements/주제 폴더>
명세서가 쓰는 마크다운만 다룬다: 제목, 문단, 목록(번호·글머리, 들여쓰기), 표, 코드 블록, `코드`, **굵게**.
ponytail: 최소 변환기. 링크·이미지·인용이 필요해지면 그때 추가
"""
import html, pathlib, re, sys

CSS = """
:root{--bg:#fff;--fg:#1f2328;--mute:#59636e;--line:#d1d9e0;--code:#f6f8fa;--accent:#0969da}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--mute:#9198a1;--line:#3d444d;--code:#151b23;--accent:#4493f8}}
body{background:var(--bg);color:var(--fg);font:16px/1.7 -apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;margin:0}
main{max-width:860px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:1.7em;border-bottom:1px solid var(--line);padding-bottom:.3em}
h2{font-size:1.3em;margin-top:2em;border-bottom:1px solid var(--line);padding-bottom:.2em}
h3{font-size:1.1em;margin-top:1.5em}
code{background:var(--code);padding:.1em .35em;border-radius:4px;font-size:.9em}
pre{background:var(--code);padding:12px 16px;border-radius:6px;overflow-x:auto}
pre code{padding:0;background:none}
table{border-collapse:collapse;width:100%;margin:1em 0;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:6px 12px;text-align:left;vertical-align:top}
th{background:var(--code)}
li{margin:.2em 0}
"""


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)


def cells(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]


def convert(md):
    lines, out, i = md.splitlines(), [], 0
    stack = []  # 열린 목록: (들여쓰기, 태그)

    def close_lists(indent=-1):
        while stack and stack[-1][0] > indent:
            out.append(f'</li></{stack.pop()[1]}>')

    while i < len(lines):
        line = lines[i]
        m_list = re.match(r'^(\s*)(-|\d+\.)\s+(.*)$', line)
        if line.startswith('```'):
            close_lists()
            j = i + 1
            while j < len(lines) and not lines[j].startswith('```'):
                j += 1
            out.append('<pre><code>' + html.escape('\n'.join(lines[i + 1:j])) + '</code></pre>')
            i = j + 1
            continue
        if m_list:
            indent, tag = len(m_list.group(1)), 'ul' if m_list.group(2) == '-' else 'ol'
            if stack and stack[-1][0] == indent:
                out.append('</li>')
            elif not stack or stack[-1][0] < indent:
                out.append(f'<{tag}>')
                stack.append((indent, tag))
            else:
                close_lists(indent)
                out.append('</li>')
            out.append('<li>' + inline(m_list.group(3)))
            i += 1
            continue
        if stack and line.startswith(' ') and line.strip():
            out.append(' ' + inline(line.strip()))
            i += 1
            continue
        close_lists()
        if m := re.match(r'^(#{1,3})\s+(.*)$', line):
            n = len(m.group(1))
            out.append(f'<h{n}>{inline(m.group(2))}</h{n}>')
        elif line.startswith('|') and i + 1 < len(lines) and re.match(r'^\|[\s:|-]+\|$', lines[i + 1].strip()):
            out.append('<table><thead><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in cells(line)) + '</tr></thead><tbody>')
            i += 2
            while i < len(lines) and lines[i].startswith('|'):
                out.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in cells(lines[i])) + '</tr>')
                i += 1
            out.append('</tbody></table>')
            continue
        elif line.strip():
            out.append(f'<p>{inline(line)}</p>')
        i += 1
    close_lists()
    return '\n'.join(out)


def main(folder):
    for md in sorted(pathlib.Path(folder).glob('*.md')):
        text = md.read_text()
        title = next((l[2:].strip() for l in text.splitlines() if l.startswith('# ')), md.stem)
        doc = (f'<!doctype html><html lang="ko"><head><meta charset="utf-8">'
               f'<meta name="viewport" content="width=device-width,initial-scale=1">'
               f'<title>{html.escape(title)}</title><style>{CSS}</style></head>'
               f'<body><main>{convert(text)}</main></body></html>\n')
        md.with_suffix('.html').write_text(doc)
        print(md.with_suffix('.html').name)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
