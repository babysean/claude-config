#!/usr/bin/env python3
"""장부 사본의 N번 절만 메인 `진행.md` 에 옮겨 붙인다. 다른 절(다른 꼬붕이 몫)은 건드리지 않는다.

팀장이 메인 체크아웃 세션에서 돌린다 — 워크트리 격리 세션은 메인 경로에 쓰지 못한다.

사용: merge_ledger.py <사본 진행.md> <메인 진행.md> <N> [<N> ...]
      merge_ledger.py --self-test
"""
import pathlib
import sys
import tempfile


def section(text: str, n: str) -> str:
    start = text.index(f"\n## {n}. ")
    end = text.find("\n## ", start + 1)
    return text[start:] if end < 0 else text[start:end]


def merge(copy: str, main: str, numbers: list[str]) -> list[str]:
    src, dst = pathlib.Path(copy).read_text(), pathlib.Path(main).read_text()
    done = []
    for n in numbers:
        new, old = section(src, n), section(dst, n)
        if "### 테스트" not in new:
            sys.exit(f"{n}번 절이 사본에서 비어 보임 — 옮기지 않음")
        dst = dst.replace(old, new)
        done.append(f"{n}번 절 {len(old.splitlines())} → {len(new.splitlines())} 줄")
    pathlib.Path(main).write_text(dst)
    return done


def self_test() -> None:
    with tempfile.TemporaryDirectory() as d:
        main, copy = pathlib.Path(d, "main.md"), pathlib.Path(d, "copy.md")
        main.write_text("# 장부\n\n## 1. 가\n\n### 테스트\n옛 1\n\n## 2. 나\n\n### 테스트\n남의 새 2\n")
        copy.write_text("# 장부\n\n## 1. 가\n\n### 테스트\n새 1\n\n## 2. 나\n\n### 테스트\n옛 2\n")
        merge(str(copy), str(main), ["1"])
        text = main.read_text()
        assert "새 1" in text and "옛 1" not in text, text
        assert "남의 새 2" in text, "다른 절을 덮었다"
    print("self-test 통과")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    elif len(sys.argv) >= 4:
        for line in merge(sys.argv[1], sys.argv[2], sys.argv[3:]):
            print(line)
    else:
        sys.exit(__doc__)
