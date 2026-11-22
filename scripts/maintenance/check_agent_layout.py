"""Validate the agent inventory against versioned and new, non-ignored files."""
import argparse
import csv
import fnmatch
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
TREE = ROOT / "agents/FILE_TREE.md"
OWNERS = {
    "whale": "고래", "crypto": "코인", "real_estate": "부동산",
    "equities": "주식", "us_small_cap_high_beta": "미국 소형·고베타 주식",
    "shared": "공용 운영·투자", "rwa_research": "독립 RWA 연구",
}
PRIVATE_PATTERNS = (".env", ".env.*", "*/.env", "*/.env.*", "private_accounts/.local/*",
                    ".local-build/*", "*accounts_stocks*.xls*", "private_accounts/*.xls*",
                    "private_accounts/*.csv", ".streamlit/secrets.toml", "trading_bot/config/user_settings.json")
IGNORE_PROBES = (".env", "private_accounts/accounts_stocks.xlsx", "private_accounts/.local/credentials.env",
                 "private_accounts/.local/bindings.json", ".local-build/account-reader")


def render_tree(rows):
    lines = ["# 전체 파일 트리", "", "분야를 펼치면 실제 경로와 원본 파일을 볼 수 있다. 이전 경로는 [파일 분류표](FILE_MAP.csv)에서 확인할 수 있다.", ""]
    for owner, title in OWNERS.items():
        paths = sorted(Path(row["path"]) for row in rows if row["owner"] == owner)
        lines.extend(["<details>", f"<summary>{title} ({len(paths)}개)</summary>", ""])
        previous = ()
        for path in paths:
            folders = path.parts[:-1]
            for depth, name in enumerate(folders):
                if previous[:depth + 1] != folders[:depth + 1]:
                    lines.append("  " * depth + f"- `{name}/`")
            target = os.path.relpath(ROOT / path, TREE.parent)
            lines.append("  " * len(folders) + f"- [{path.name}](<{target}>)")
            previous = folders
        lines.extend(["", "</details>", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-tree", action="store_true", help="Refresh FILE_TREE.md from FILE_MAP.csv")
    args = parser.parse_args()
    with (ROOT / "agents/FILE_MAP.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))

    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
    )
    names = os.fsdecode(output).split("\0")
    inventory_names = [r[k] for r in rows for k in ("path", "previous_path")]
    if any(fnmatch.fnmatchcase(name, pattern) for name in names + inventory_names for pattern in PRIVATE_PATTERNS):
        print("Private input found among Git candidates or inventory entries.", file=sys.stderr)
        return 1
    ignored = subprocess.run(["git", "check-ignore", "--no-index", "-z", "--stdin"], cwd=ROOT,
                             input=os.fsencode("\0".join(IGNORE_PROBES) + "\0"), capture_output=True)
    if ignored.returncode or set(os.fsdecode(ignored.stdout).split("\0")) != {*IGNORE_PROBES, ""}:
        print("Private input ignore rules are incomplete.", file=sys.stderr)
        return 1

    tree = render_tree(rows)
    if args.write_tree:
        TREE.write_text(tree, encoding="utf-8")
    listed = set()
    errors = []
    principles = Path("investor-principles/SKILL.md")
    if (ROOT / ".agents/skills" / principles).read_bytes() != (ROOT / "branch/investor_agent/skills" / principles).read_bytes():
        errors.append("Investor principles copies differ")
    if not TREE.exists() or TREE.read_text(encoding="utf-8") != tree:
        errors.append("Refresh the file tree with --write-tree")
    for row in rows:
        if row["owner"] not in OWNERS:
            errors.append(f"Unknown owner: {row['owner']}")
        path = ROOT / row["path"]
        if path in listed:
            errors.append(f"Duplicate entry: {path.relative_to(ROOT)}")
        listed.add(path)
        if path.resolve() != path or not path.is_file():
            errors.append(f"Invalid canonical file: {row['path']}")
        if row["previous_path"]:
            old = ROOT / row["previous_path"]
            if not old.is_file() or old.resolve() != path:
                errors.append(f"Invalid compatibility path: {row['previous_path']}")

    current = set()
    for name in names:
        if not name:
            continue
        path = ROOT / name
        if path.is_symlink() and not path.resolve().is_relative_to(ROOT):
            errors.append(f"Compatibility link exits repository: {name}")
        elif path.is_file():
            current.add(path.resolve())
        elif not (path.is_symlink() and path.is_dir()):
            errors.append(f"Missing file or broken link: {name}")

    for path in sorted(current - listed):
        errors.append(f"Missing inventory entry: {os.path.relpath(path, ROOT)}")
    for path in sorted(listed - current):
        errors.append(f"Outside Git inventory: {os.path.relpath(path, ROOT)}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"{len(listed)} canonical files; all compatibility paths verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
