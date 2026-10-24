#!/usr/bin/env python3
"""Find live internships and new-grad jobs and read their requirements, for the proof-of-skill Skill.

Search uses the SimplifyJobs internship and new-grad lists on GitHub (public, updated daily). A posting's
description comes from the public Greenhouse, Lever, Ashby or Workday job APIs, or the posting page itself.
No keys or sign-in. Python 3.9+ standard library only.

State under HOME: ~/.config/proof-of-skill/ (profile.json, shown.json). Downloaded lists are cached in
~/.cache/proof-of-skill/ for 6 hours. --sample uses assets/ and never reads or writes the student's state.

Exit codes: 0 ok, 2 bad arguments, 3 no profile saved, 4 network error, 5 posting closed or unreadable.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LISTS = {
    "internship": "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/.github/scripts/listings.json",
    "new-grad": "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json",
}
ASSETS = Path(__file__).resolve().parent.parent / "assets"
CONFIG = Path.home() / ".config" / "proof-of-skill"
CACHE = Path.home() / ".cache" / "proof-of-skill"
CACHE_HOURS = 6
USER_AGENT = "proof-of-skill/1.0 (+https://github.com)"
SECTION_WORDS = (r"(basic qualifications|minimum qualifications|preferred qualifications|qualifications|requirements|"
                 r"what you'll need|what you will need|what we're looking for|what we are looking for|who you are|"
                 r"you might be a fit|about you|you have|you bring|skills)")
HEADING = re.compile(r"(?im)^[ \t\-•*]*[\w ,&'’]{0,30}?" + SECTION_WORDS + r"[^\n]{0,40}$")
SECTION = re.compile(SECTION_WORDS, re.I)
TERM = re.compile(r"(spring|summer|fall|winter)\s+(20\d\d)", re.I)
TERM_ENDS = {"spring": 5, "summer": 8, "fall": 12, "winter": 15}  # month the term ends; winter runs into next year
DETAIL_CHARS = 1200
ELIGIBILITY = re.compile(
    r"sponsor|authori[sz]ed to work|work authori[sz]ation|citizen|permanent resident|green card|\bvisa\b|"
    r"\bF-1\b|\bCPT\b|\bOPT\b|clearance|\bGPA\b|graduat(e|ing|ion) (date|between|by|in)|return(ing)? to school",
    re.I,
)


def fail(message: str, code: int):
    print(message, file=sys.stderr)
    sys.exit(code)


def get(url: str, accept: str = "application/json") -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1))


# ---------- listings ----------

def load_list(kind: str) -> list:
    cached = CACHE / f"{kind}.json"
    fresh = cached.exists() and time.time() - cached.stat().st_mtime < CACHE_HOURS * 3600
    if not fresh:
        try:
            data = get(LISTS[kind])
            json.loads(data)  # don't cache a broken download
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_bytes(data)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            if not cached.exists():
                fail(f"Could not download the {kind} list ({type(exc).__name__}). Try again later.", 4)
            print(f"Note: using a cached {kind} list; the download failed.", file=sys.stderr)
    return read_json(cached, [])


def listings(kinds: list, sample: bool) -> list:
    if sample:
        rows = read_json(ASSETS / "sample_listings.json", [])
        return [r for r in rows if r.get("kind") in kinds]
    rows = []
    for kind in kinds:
        for r in load_list(kind):
            if r.get("active") and r.get("is_visible", True):
                rows.append(dict(r, kind=kind))
    return rows


def short_id(row: dict) -> str:
    return str(row.get("id", ""))[:8]


def term_over(term: str, now: datetime) -> bool:
    """True for a term like 'Spring 2026' that has already ended; unknown terms ('N/A') count as open."""
    m = TERM.search(term)
    if not m:
        return False
    year, month = int(m.group(2)), TERM_ENDS[m.group(1).lower()]
    year, month = year + (month - 1) // 12, (month - 1) % 12 + 1
    return (year, month) < (now.year, now.month)


def keyword_score(row: dict, keywords: list) -> int:
    title = (row.get("title") or "").lower()
    rest = " ".join([row.get("category") or "", row.get("company_name") or ""]).lower()
    score = 0
    for kw in keywords:
        pattern = r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])"
        if re.search(pattern, title):
            score += 3
        elif re.search(pattern, rest):
            score += 1
    return score


def cmd_search(args) -> int:
    kinds = ["internship", "new-grad"] if args.type == "all" else [args.type]
    keywords = [k.strip().lower() for k in (args.keywords or "").split(",") if k.strip()]
    places = [p.strip().lower() for p in args.location or [] if p.strip()]
    shown = set() if args.sample or args.include_shown else set(read_json(CONFIG / "shown.json", []))
    now = datetime.now(timezone.utc)
    since = time.time() - args.days * 86400 if args.days else 0

    picked = []
    for row in listings(kinds, args.sample):
        if short_id(row) in shown:
            continue
        if since and (row.get("date_posted") or 0) < since:
            continue
        locations = " | ".join(row.get("locations") or []).lower()
        if places and not any(p in locations for p in places):
            continue
        degrees = [d.lower() for d in row.get("degrees") or []]
        if args.degree and degrees and not any(d.startswith(args.degree[:4]) for d in degrees):
            continue
        terms = row.get("terms") or []
        if terms and all(term_over(t, now) for t in terms):
            continue
        if args.term and not any(args.term.lower() in t.lower() for t in terms):
            continue
        score = keyword_score(row, keywords) if keywords else 1
        if score:
            picked.append((score, row.get("date_posted") or 0, row))

    picked.sort(key=lambda t: (t[0], t[1]), reverse=True)
    if not picked:
        print("No matching postings. Try fewer or broader keywords, another location, or --type all.")
        return 0
    print(f"{len(picked)} matching postings; best {min(args.limit, len(picked))}:")
    for _, posted, row in picked[: args.limit]:
        when = datetime.fromtimestamp(posted, timezone.utc).strftime("%b %d") if posted else "?"
        terms = ", ".join(t for t in row.get("terms") or [] if t != "N/A")
        place = "; ".join((row.get("locations") or [])[:3])
        bits = [short_id(row), row.get("title", "").strip(), row.get("company_name", ""), place,
                terms or row["kind"], f"posted {when}"]
        print(" | ".join(b for b in bits if b))
        print(f"  {row.get('url')}")
    return 0


# ---------- details ----------

def strip_html(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?i)<li[^>]*>", "\n- ", text)
    text = re.sub(r"(?i)<br\s*/?>|</(p|div|li|ul|ol|h[1-6])>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def from_greenhouse(url: str):
    m = re.search(r"greenhouse\.io/(?:embed/job_app\?for=)?([^/?#]+)/jobs/(\d+)", url)
    if not m:
        return None
    host = "boards-api.eu.greenhouse.io" if ".eu." in url else "boards-api.greenhouse.io"
    job = json.loads(get(f"https://{host}/v1/boards/{m.group(1)}/jobs/{m.group(2)}"))
    return job.get("title", ""), strip_html(job.get("content", ""))


def from_lever(url: str):
    m = re.search(r"jobs\.(eu\.)?lever\.co/([^/?#]+)/([0-9a-f-]{36})", url)
    if not m:
        return None
    host = "api.eu.lever.co" if m.group(1) else "api.lever.co"
    job = json.loads(get(f"https://{host}/v0/postings/{m.group(2)}/{m.group(3)}"))
    parts = [job.get("descriptionPlain", "")]
    for item in job.get("lists") or []:
        parts.append(item.get("text", "") + "\n" + strip_html(item.get("content", "")))
    parts.append(job.get("additionalPlain", ""))
    return job.get("text", ""), "\n".join(p for p in parts if p)


def from_ashby(url: str):
    m = re.search(r"jobs\.ashbyhq\.com/([^/?#]+)/([0-9a-f-]{36})", url)
    if not m:
        return None
    board = json.loads(get(f"https://api.ashbyhq.com/posting-api/job-board/{m.group(1)}"))
    for job in board.get("jobs") or []:
        if job.get("id") == m.group(2):
            return job.get("title", ""), job.get("descriptionPlain") or strip_html(job.get("descriptionHtml", ""))
    raise urllib.error.HTTPError(url, 404, "not on the board", None, None)


def from_workday(url: str):
    parsed = urllib.parse.urlparse(url)
    if "myworkdayjobs.com" not in parsed.netloc:
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if parts and re.match(r"^[a-z]{2}-[A-Z]{2}$", parts[0]):
        parts = parts[1:]
    if len(parts) < 2:
        return None
    tenant = parsed.netloc.split(".")[0]
    job = json.loads(get(f"https://{parsed.netloc}/wday/cxs/{tenant}/{parts[0]}/{'/'.join(parts[1:])}"))
    info = job.get("jobPostingInfo") or {}
    return info.get("title", ""), strip_html(info.get("jobDescription", ""))


def from_page(url: str):
    page = get(url, accept="text/html").decode("utf-8", "replace")
    title = re.search(r"(?is)<title[^>]*>(.*?)</title>", page)
    return strip_html(title.group(1)) if title else "", strip_html(page)


def requirements(text: str) -> str:
    """The qualifications part of a description when there is one, else its start."""
    text = text.replace("\u2019", "'")
    match = HEADING.search(text, 200) or SECTION.search(text, 200)
    start = match.start() if match else 0
    chunk = text[start:start + DETAIL_CHARS]
    return chunk + (" ..." if len(text) > start + DETAIL_CHARS else "")


def eligibility(text: str) -> str:
    """Sentences about work authorization, sponsorship, GPA or graduation dates, wherever they appear."""
    text = text.replace("\u2019", "'")
    found = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n", text):
        sentence = sentence.strip(" -•*")
        if ELIGIBILITY.search(sentence) and 10 < len(sentence) < 400 and sentence not in found:
            found.append(sentence)
    return "\n".join(f"- {f}" for f in found[:5])


def resolve(ref: str, sample: bool):
    if ref.startswith("https://"):
        return ref, None
    for row in listings(["internship", "new-grad"], sample):
        if short_id(row) == ref[:8]:
            return row.get("url"), row
    return None, None


def cmd_details(args) -> int:
    if len(args.refs) > 5:
        fail("Ask for at most 5 postings at a time.", 2)
    sample = read_json(ASSETS / "sample_details.json", {}) if args.sample else {}
    worst = 0
    for ref in args.refs:
        url, row = resolve(ref, args.sample)
        label = f"[{ref}]"
        if row:
            label += f" {row.get('title', '').strip()} at {row.get('company_name', '')}"
        if not url:
            print(f"{label}\nNot found. Use an id from the last search or the posting's https:// link.\n")
            worst = max(worst, 5)
            continue
        try:
            if args.sample:
                title, text = row.get("title", ""), sample.get(short_id(row), "")
            else:
                found = None
                for reader in (from_greenhouse, from_lever, from_ashby, from_workday):
                    found = reader(url)
                    if found:
                        break
                title, text = found or from_page(url)
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 410):
                print(f"{label}\nThis posting is closed or was removed.\n  {url}\n")
            else:
                print(f"{label}\nThe site blocked reading it here (HTTP {exc.code}). Open it in the browser.\n  {url}\n")
            worst = max(worst, 5)
            continue
        except (urllib.error.URLError, OSError, ValueError) as exc:
            print(f"{label}\nCould not read it ({type(exc).__name__}). Open it in the browser instead.\n  {url}\n")
            worst = max(worst, 4)
            continue
        if len(text) < 300:
            print(f"{label}\nThe page has no readable description (it may need a browser). Open it in the browser.\n  {url}\n")
            worst = max(worst, 5)
            continue
        if not row and title:
            label += f" {title}"
        rules = eligibility(text)
        rules = f"Eligibility mentions:\n{rules}" if rules else "Eligibility mentions: none found in the description."
        print(f"{label}\n  {url}\n{requirements(text)}\n{rules}\n")
    return worst


# ---------- state ----------

def cmd_shown(args) -> int:
    path = CONFIG / "shown.json"
    seen = read_json(path, [])
    seen.extend(r[:8] for r in args.ids if r[:8] not in seen)
    write_json(path, seen[-2000:])
    print(f"Marked {len(args.ids)} as shown; later searches skip them.")
    return 0


def cmd_profile(args) -> int:
    path = CONFIG / "profile.json"
    if args.action == "show":
        profile = read_json(path, None)
        if not profile:
            fail("No profile saved yet. Build it from the student's Canvas courses first.", 3)
        print(json.dumps(profile, indent=1))
        return 0
    raw = Path(args.file).read_text() if args.file else sys.stdin.read()
    try:
        profile = json.loads(raw)
    except ValueError as exc:
        fail(f"The profile is not valid JSON: {exc}", 2)
    if not isinstance(profile, dict) or not isinstance(profile.get("skills"), list):
        fail('The profile needs a "skills" list, e.g. {"skills": [{"skill": "SQL", "evidence": [...]}]}.', 2)
    profile["saved"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    write_json(path, profile)
    print(f"Saved the profile with {len(profile['skills'])} skills.")
    return 0


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="find live internships and new-grad jobs")
    s.add_argument("--type", choices=["internship", "new-grad", "all"], default="all")
    s.add_argument("--keywords", help="comma-separated skills or role words, e.g. 'python,sql,data analyst'")
    s.add_argument("--location", action="append", help="part of a location, e.g. 'Phoenix' or 'Remote'; repeat for more")
    s.add_argument("--degree", choices=["bachelors", "masters", "phd"], help="skip postings that need another degree")
    s.add_argument("--term", help="internship term, e.g. 'Summer 2027'")
    s.add_argument("--days", type=int, help="only postings from the last N days")
    s.add_argument("--limit", type=int, default=15, choices=range(1, 21), metavar="1-20")
    s.add_argument("--include-shown", action="store_true", help="also list postings already shown to the student")
    s.add_argument("--sample", action="store_true", help="offline demo with assets/sample_listings.json")
    s.set_defaults(fn=cmd_search)

    d = sub.add_parser("details", help="read the requirements of up to 5 postings")
    d.add_argument("refs", nargs="+", help="ids from search, or https:// posting links")
    d.add_argument("--sample", action="store_true", help="offline demo with assets/sample_details.json")
    d.set_defaults(fn=cmd_details)

    m = sub.add_parser("shown", help="remember postings already texted to the student")
    m.add_argument("ids", nargs="+")
    m.set_defaults(fn=cmd_shown)

    p = sub.add_parser("profile", help="save or show the student's skills profile")
    p.add_argument("action", choices=["save", "show"])
    p.add_argument("--file", help="JSON file to save (default: read standard input)")
    p.set_defaults(fn=cmd_profile)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
