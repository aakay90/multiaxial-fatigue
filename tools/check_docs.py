"""Check local Markdown destinations without network access or dependencies.

External links, code spans/fences and frozen literature/provenance documents are
excluded. This checks the maintained documentation's file and fragment links;
it does not certify the availability or scientific accuracy of external sources.
"""

from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
FROZEN = {"docs/research", "docs/catalogue"}


def prose(text):
    text = re.sub(r"^```.*?^```[^\n]*", lambda m: "\n" * m[0].count("\n"), text, flags=re.M | re.S)
    return re.sub(r"`[^`\n]+`", "", text)


def anchors(text):
    """Explicit anchors and GitHub-style heading slugs, including duplicates."""
    found = set(re.findall(r"<a\s+(?:id|name)=[\"\']([^\"\']+)", text))
    counts = {}
    for title in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", text, flags=re.M):
        title = re.sub(r"<[^>]*>", "", title).lower()
        slug = re.sub(r"[^\w\- ]", "", title).replace(" ", "-")
        n = counts.get(slug, 0)
        counts[slug] = n + 1
        found.add(f"{slug}-{n}" if n else slug)
    return found


def main():
    tracked = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
        )
        .decode()
        .split("\0")
    )
    # Include untracked work in progress, respecting the repository ignore rules.
    paths = sorted(set(tracked))
    errors, checked = [], 0
    cache = {}
    for name in paths:
        if not name.endswith(".md") or any(name.startswith(p + "/") for p in FROZEN):
            continue
        source = ROOT / name
        if not source.is_file():
            continue
        text = prose(source.read_text(encoding="utf-8"))
        for match in re.finditer(r"\[[^\]\n]*\]\(([^\s]+?)(?:\s+\"[^\"]*\")?\)", text):
            dest = match.group(1)
            url = urlsplit(dest)
            if url.scheme or url.netloc:
                continue
            target = (source.parent / unquote(url.path)).resolve() if url.path else source
            line = text.count("\n", 0, match.start()) + 1
            checked += 1
            if not target.exists():
                errors.append(f"{name}:{line}: missing {dest}")
            elif url.fragment and target.suffix == ".md":
                if target not in cache:
                    cache[target] = anchors(target.read_text(encoding="utf-8"))
                if unquote(url.fragment) not in cache[target]:
                    errors.append(f"{name}:{line}: missing fragment {dest}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"{checked} local documentation links OK (external links and frozen provenance excluded)")


if __name__ == "__main__":
    main()
