#!/usr/bin/env python3
"""Send a personalized weekly digest of open-access NBER working papers."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import email.message
import html
import json
import math
import os
import re
import smtplib
import ssl
import sys
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


BASE = "https://data.nber.org/nber_paper_chapter_metadata/tsv"
FILES = {
    "title": "title.tsv",
    "abstract": "abs.tsv",
    "date": "date.tsv",
    "authors": "auths.tsv",
    "programs": "prog.tsv",
}
TOKEN_RE = re.compile(r"[a-z][a-z0-9'-]{2,}")
STOPWORDS = {
    "the", "and", "for", "that", "with", "from", "this", "are", "was", "were",
    "have", "has", "had", "into", "their", "they", "using", "use", "our", "but",
    "not", "can", "these", "than", "between", "which", "also", "more", "paper",
    "study", "results", "find", "show", "effects", "effect", "evidence", "model",
}

# Windows commonly starts Python with a legacy console encoding. NBER author
# names frequently contain characters outside it, so keep previews Unicode-safe.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


@dataclass
class Paper:
    paper_id: str
    title: str
    abstract: str
    issue_date: dt.date
    authors: str = ""
    programs: tuple[str, ...] = ()
    score: float = 0.0
    reasons: tuple[str, ...] = ()

    @property
    def page_url(self) -> str:
        return f"https://www.nber.org/papers/{self.paper_id}"

    @property
    def pdf_url(self) -> str:
        return f"https://www.nber.org/system/files/working_papers/{self.paper_id}/{self.paper_id}.pdf"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
    temporary.replace(path)


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "nber-weekly-reader/1.0"})
    with urllib.request.urlopen(request, timeout=45) as response:
        destination.write_bytes(response.read())


def refresh_metadata(cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    for filename in FILES.values():
        download(f"{BASE}/{filename}", cache_dir / filename)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        # NBER titles may contain unmatched straight quotes. TSV quoting is not
        # needed here, and disabling it prevents one title from swallowing many
        # subsequent records.
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


def first_value(row: dict[str, str], names: tuple[str, ...]) -> str:
    lowered = {k.lower(): (v or "").strip() for k, v in row.items()}
    for name in names:
        if lowered.get(name):
            return lowered[name]
    return ""


def paper_id(row: dict[str, str]) -> str:
    return first_value(row, ("paper", "paper_id", "id"))


def parse_date(raw: str) -> dt.date | None:
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%B %Y", "%b %Y", "%Y-%m"):
        try:
            return dt.datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    return None


def load_papers(cache_dir: Path) -> list[Paper]:
    tables = {name: read_tsv(cache_dir / filename) for name, filename in FILES.items()}
    titles = {paper_id(r): first_value(r, ("title",)) for r in tables["title"]}
    abstracts = {paper_id(r): first_value(r, ("abstract", "abs")) for r in tables["abstract"]}
    dates = {paper_id(r): parse_date(first_value(r, ("issue_date", "date"))) for r in tables["date"]}

    authors: dict[str, list[str]] = {}
    for row in tables["authors"]:
        authors.setdefault(paper_id(row), []).append(first_value(row, ("name", "author")))
    programs: dict[str, list[str]] = {}
    for row in tables["programs"]:
        programs.setdefault(paper_id(row), []).append(first_value(row, ("program", "name")))

    result = []
    for pid, title in titles.items():
        if not pid.startswith("w") or not title or not dates.get(pid):
            continue
        result.append(Paper(
            paper_id=pid,
            title=title,
            abstract=abstracts.get(pid, ""),
            issue_date=dates[pid],
            authors=", ".join(x for x in authors.get(pid, []) if x),
            programs=tuple(dict.fromkeys(x for x in programs.get(pid, []) if x)),
        ))
    return result


def months_ago(day: dt.date, months: int) -> dt.date:
    year = day.year
    month = day.month - months
    while month <= 0:
        year -= 1
        month += 12
    last_day = (dt.date(year + (month == 12), 1 if month == 12 else month + 1, 1) - dt.timedelta(days=1)).day
    return dt.date(year, month, min(day.day, last_day))


def tokens(text: str) -> list[str]:
    return [x for x in TOKEN_RE.findall(text.lower()) if x not in STOPWORDS]


def phrase_hits(text: str, preferences: dict) -> tuple[float, list[str]]:
    lowered = text.lower()
    score = 0.0
    reasons: list[str] = []
    for phrase, weight in preferences.get("topics", {}).items():
        if phrase.lower() in lowered:
            score += float(weight)
            reasons.append(phrase)
    for phrase in preferences.get("avoid_topics", []):
        if phrase.lower() in lowered:
            score -= 8.0
    return score, reasons


def learned_profile(papers: list[Paper], liked_ids: set[str]) -> Counter[str]:
    profile: Counter[str] = Counter()
    for paper in papers:
        if paper.paper_id in liked_ids:
            profile.update(tokens(f"{paper.title} {paper.title} {paper.abstract}"))
    return Counter(dict(profile.most_common(80)))


def score_papers(papers: list[Paper], preferences: dict) -> list[Paper]:
    liked_ids = set(preferences.get("liked_papers", []))
    profile = learned_profile(papers, liked_ids)
    for title in preferences.get("liked_titles", []):
        # Repeating the title gives explicit examples meaningful weight even
        # when they are conference papers rather than NBER Working Papers.
        profile.update(tokens(f"{title} {title} {title}"))
    preferred_programs = {x.lower() for x in preferences.get("programs", [])}
    preferred_authors = [x.lower() for x in preferences.get("authors", [])]

    for paper in papers:
        text = f"{paper.title} {paper.title} {paper.abstract}"
        score, reasons = phrase_hits(text, preferences)
        program_hits = [p for p in paper.programs if p.lower() in preferred_programs]
        score += 3.0 * len(program_hits)
        reasons.extend(program_hits)
        for author in preferred_authors:
            if author in paper.authors.lower():
                score += 4.0
                reasons.append(author)
        counts = Counter(tokens(text))
        if profile:
            overlap = sum(min(counts[t], 3) * math.log1p(profile[t]) for t in counts if t in profile)
            score += min(overlap / 4.0, 8.0)
            if overlap:
                reasons.append("与你喜欢的论文相似")
        paper.score = round(score, 2)
        paper.reasons = tuple(dict.fromkeys(reasons))
    return papers


def select_papers(papers: list[Paper], config: dict, state: dict, today: dt.date) -> list[Paper]:
    settings = config.get("selection", {})
    count = int(settings.get("papers_per_week", 6))
    cohort_count = min(int(settings.get("newly_open_papers", 4)), count)
    cutoff = months_ago(today, int(settings.get("open_access_months", 18)))
    earliest = dt.date.fromisoformat(settings.get("earliest_date", "1973-01-01"))
    sent = set(state.get("sent", {}))
    eligible = [p for p in papers if earliest <= p.issue_date <= cutoff and p.paper_id not in sent]
    scored = score_papers(eligible, config.get("preferences", {}))
    if not scored:
        return []
    # NBER releases papers in weekly batches. The newest eligible release date
    # is the batch that has just crossed the open-access boundary.
    latest_release = max(p.issue_date for p in scored)
    cohort = [p for p in scored if p.issue_date == latest_release]
    archive = [p for p in scored if p.issue_date != latest_release]
    key = lambda p: (p.score, p.issue_date, p.paper_id)
    cohort.sort(key=key, reverse=True)
    archive.sort(key=key, reverse=True)
    selected = cohort[:cohort_count]
    selected.extend(archive[: count - len(selected)])
    if len(selected) < count:
        selected.extend(cohort[cohort_count: cohort_count + count - len(selected)])
    return selected[:count]


def excerpt(text: str, length: int = 520) -> str:
    clean = " ".join(text.split())
    return clean if len(clean) <= length else clean[:length].rsplit(" ", 1)[0] + "…"


def render_email(papers: list[Paper], today: dt.date) -> tuple[str, str, str]:
    subject = f"本周 NBER 免费论文精选 · {today.isoformat()}"
    plain_lines = [subject, "", "这些论文均已超过 NBER 的18个月开放期。", ""]
    cards = []
    toc = []
    newest = max(p.issue_date for p in papers)
    for i, p in enumerate(papers, 1):
        reason = "、".join(p.reasons[:4]) or "综合匹配"
        group = "刚开放的一周" if p.issue_date == newest else "历史精选"
        toc.append(f'<a href="#paper-{i}" style="display:block;padding:10px 0;border-bottom:1px solid #e5e7eb;color:#102a43;text-decoration:none"><span style="color:#829ab1;margin-right:8px">{i:02d}</span>{html.escape(p.title)}</a>')
        plain_lines += [
            f"{i}. {p.title}",
            f"作者：{p.authors or '未列出'} · {p.issue_date:%Y-%m} · 匹配：{reason}",
            excerpt(p.abstract),
            f"论文页：{p.page_url}",
            f"PDF：{p.pdf_url}", "",
        ]
        cards.append(f"""
        <article id="paper-{i}" style="margin:0 0 24px;padding:24px;background:#ffffff;border:1px solid #d9e2ec;border-radius:14px;box-shadow:0 6px 18px rgba(16,42,67,.06)">
          <div style="font-size:12px;font-weight:700;letter-spacing:.04em;color:#2f80ed;text-transform:uppercase">{group} · {p.issue_date:%Y-%m-%d}</div>
          <h2 style="font-size:20px;line-height:1.4;margin:10px 0 6px;color:#102a43">{html.escape(p.title)}</h2>
          <div style="font-size:14px;color:#627d98">{html.escape(p.authors or '未列出作者')}</div>
          <div style="margin:14px 0 0;font-size:12px;color:#486581">为什么推荐：{html.escape(reason)}</div>
          <p style="font-size:15px;line-height:1.75;color:#334e68;margin:12px 0 18px">{html.escape(excerpt(p.abstract))}</p>
          <a href="{p.pdf_url}" style="display:inline-block;padding:10px 15px;background:#102a43;color:white;text-decoration:none;border-radius:8px;font-weight:700">阅读免费 PDF</a>
          <a href="{p.page_url}" style="margin-left:14px;color:#2f80ed;text-decoration:none">NBER 摘要页 →</a>
        </article>""")
    html_body = f"""<!doctype html><html><body style="margin:0;background:#f0f4f8;font-family:Arial,'Microsoft YaHei',sans-serif;color:#102a43">
      <div style="max-width:760px;margin:0 auto;padding:32px 16px">
      <header style="padding:30px;background:linear-gradient(135deg,#102a43,#243b53);border-radius:16px;color:white">
        <div style="font-size:12px;letter-spacing:.12em;color:#9fb3c8">NBER WEEKLY READER</div>
        <h1 style="font-size:29px;margin:10px 0 8px">本周免费论文精选</h1>
        <p style="margin:0;color:#d9e2ec;line-height:1.6">追踪刚跨过18个月开放线的论文，并加入少量与你交易与实证研究兴趣高度匹配的历史精选。</p>
      </header>
      <section style="margin:20px 0 28px;padding:22px 24px;background:white;border-radius:14px;border:1px solid #d9e2ec">
        <div style="font-size:13px;font-weight:700;color:#627d98;margin-bottom:8px">本期目录 · 点击标题跳转</div>
        {''.join(toc)}
      </section>
      <section>{''.join(cards)}</section>
      <p style="font-size:12px;color:#829ab1;text-align:center;padding:8px">来源：NBER 官方元数据；本邮件不是 NBER 官方通讯。</p>
      </div>
    </body></html>"""
    return subject, "\n".join(plain_lines), html_body


def send_email(config: dict, subject: str, plain: str, html_body: str) -> None:
    mail = config["email"]
    password_env = mail.get("password_env", "NBER_SMTP_PASSWORD")
    password = os.environ.get(password_env)
    if not password:
        raise RuntimeError(f"缺少环境变量 {password_env}")
    message = email.message.EmailMessage()
    message["Subject"] = subject
    message["From"] = mail["from"]
    message["To"] = mail["to"]
    message.set_content(plain)
    message.add_alternative(html_body, subtype="html")
    context = ssl.create_default_context()
    host, port = mail["smtp_host"], int(mail.get("smtp_port", 465))
    with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as smtp:
        smtp.login(mail.get("username", mail["from"]), password)
        smtp.send_message(message)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--refresh", action="store_true", help="重新下载 NBER 官方元数据")
    parser.add_argument("--send", action="store_true", help="实际发送邮件；默认只生成预览")
    parser.add_argument("--force", action="store_true", help="忽略本周已发送保护")
    parser.add_argument("--today", help="测试用日期 YYYY-MM-DD")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_json(config_path)
    root = config_path.parent
    cache_dir = root / config.get("cache_dir", "data")
    state_path = root / config.get("state_file", "state.json")
    preview_path = root / config.get("preview_file", "preview.html")
    if args.refresh or any(not (cache_dir / f).exists() for f in FILES.values()):
        refresh_metadata(cache_dir)
    papers = load_papers(cache_dir)
    state = load_json(state_path) if state_path.exists() else {"sent": {}}
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    week_key = f"{today.isocalendar().year}-W{today.isocalendar().week:02d}"
    if args.send and not args.force and state.get("last_sent_week") == week_key:
        print(f"{week_key} 已发送过，本次不重复发送。")
        return 0
    selected = select_papers(papers, config, state, today)
    if not selected:
        print("没有找到尚未发送的合格论文。")
        return 0
    subject, plain, html_body = render_email(selected, today)
    preview_path.write_text(html_body, encoding="utf-8")
    print(plain)
    print(f"\nHTML 预览：{preview_path}")
    if args.send:
        send_email(config, subject, plain, html_body)
        state.setdefault("sent", {}).update({p.paper_id: today.isoformat() for p in selected})
        state["last_sent_week"] = week_key
        save_json(state_path, state)
        print("邮件已发送，历史记录已更新。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1)

