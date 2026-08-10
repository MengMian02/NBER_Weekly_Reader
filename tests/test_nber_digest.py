import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nber_digest import Paper, months_ago, read_tsv, render_email, select_papers


class DigestTests(unittest.TestCase):
    def test_month_cutoff_handles_month_end(self):
        self.assertEqual(months_ago(dt.date(2026, 8, 31), 18), dt.date(2025, 2, 28))

    def test_selects_open_matching_and_unsent(self):
        papers = [
            Paper("w1", "Monetary Policy and Inflation", "Central bank inflation.", dt.date(2020, 1, 1)),
            Paper("w2", "Unrelated", "Other work.", dt.date(2020, 1, 1)),
            Paper("w3", "New Inflation Paper", "Inflation.", dt.date(2026, 1, 1)),
        ]
        config = {
            "selection": {"papers_per_week": 2, "open_access_months": 18, "earliest_date": "1990-01-01"},
            "preferences": {"topics": {"inflation": 5}, "programs": [], "authors": [], "liked_papers": []},
        }
        selected = select_papers(papers, config, {"sent": {"w2": "2025-01-01"}}, dt.date(2026, 8, 10))
        self.assertEqual([p.paper_id for p in selected], ["w1"])

    def test_email_contains_official_links(self):
        paper = Paper("w12345", "A Paper", "An abstract.", dt.date(2020, 1, 1), "A. Author")
        _, plain, html = render_email([paper], dt.date(2026, 8, 10))
        self.assertIn("https://www.nber.org/papers/w12345", plain)
        self.assertIn("w12345.pdf", html)

    def test_unmatched_quote_does_not_swallow_tsv_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "title.tsv"
            path.write_text('paper\ttitle\nw1\t"An unmatched title\nw2\tA second title\n', encoding="utf-8")
            rows = read_tsv(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1]["paper"], "w2")

    def test_hybrid_selection_uses_new_cohort_and_archive(self):
        papers = [
            Paper("w10", "AI Forecasting", "financial markets", dt.date(2025, 2, 6)),
            Paper("w11", "Interest Rates", "monetary policy", dt.date(2025, 2, 6)),
            Paper("w12", "Older Econometrics", "econometrics", dt.date(2020, 1, 1)),
        ]
        config = {
            "selection": {"papers_per_week": 3, "newly_open_papers": 2, "open_access_months": 18, "earliest_date": "1990-01-01"},
            "preferences": {"topics": {"econometrics": 9, "AI": 7, "interest rates": 7}},
        }
        selected = select_papers(papers, config, {"sent": {}}, dt.date(2026, 8, 10))
        self.assertEqual({p.paper_id for p in selected[:2]}, {"w10", "w11"})
        self.assertEqual(selected[2].paper_id, "w12")


if __name__ == "__main__":
    unittest.main()

