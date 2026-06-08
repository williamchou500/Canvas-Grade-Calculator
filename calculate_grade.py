import re
from bs4 import BeautifulSoup
from collections import defaultdict


# -----------------------------
# Helpers
# -----------------------------
def parse_float(text):
    if text is None:
        return None
    try:
        return float(text.strip())
    except:
        return None


def normalize(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def extract_possible(full_text, cell):
    # -----------------------------
    # 1. Standard "/ X"
    # -----------------------------
    match = re.search(r"/\s*([0-9]+(?:\.[0-9]+)?)", full_text)
    if match:
        return float(match.group(1))

    # -----------------------------
    # 2. Look for "out of X" (Canvas sometimes uses this internally)
    # -----------------------------
    match = re.search(r"out of\s*([0-9]+(?:\.[0-9]+)?)", full_text, re.I)
    if match:
        return float(match.group(1))

    # -----------------------------
    # 3. FALLBACK: infer from visible score patterns
    # (VERY IMPORTANT for finals & quizzes)
    # -----------------------------
    # Example patterns:
    # 87.5% 87.5 100% 100.0 100 100
    perc_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", full_text)

    if perc_match:
        percent = float(perc_match.group(1))

        # try hidden DOM hints (Canvas stores raw points sometimes)
        hidden = cell.select_one(".original_score")
        if hidden:
            earned = float(hidden.get_text(strip=True))

            # assume percent = earned / possible
            if percent > 0:
                possible = earned / (percent / 100.0)
                return possible

    # -----------------------------
    # 4. LAST RESORT: treat as 100% single-point assignment
    # (prevents dropping finals)
    # -----------------------------
    return None


def extract_score(cell, debug_label=""):
    full_text = cell.get_text(" ", strip=True)

    earned = None
    possible = None

    # -------------------------
    # earned
    # -------------------------
    for sel in [".original_score", ".what_if_score"]:
        tag = cell.select_one(sel)
        if tag:
            earned = parse_float(tag.get_text(strip=True))
            if earned is not None:
                break

    if earned is None:
        grade = cell.select_one(".grade")
        if grade:
            earned = parse_float(grade.get_text(strip=True))

    if earned is None:
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)", full_text)
        if m:
            earned = float(m.group(1))

    # -------------------------
    # possible (FIXED)
    # -------------------------
    possible = extract_possible(full_text, cell)

    # DEBUG ONLY WHEN FAILING
    if possible is None or "final" in full_text.lower():
        print("\nFINAL PARSE DEBUG")
        print(debug_label)
        print(full_text)
        print("earned:", earned)
        print("possible:", possible)
        print("-" * 60)

    return earned, possible


# -----------------------------
# Main
# -----------------------------
def main(file_path):
    print("\nLOADING FILE")
    print("=" * 80)
    print(file_path)

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    # -----------------------------
    # WEIGHTS
    # -----------------------------
    print("\nWEIGHT DEBUG")
    print("=" * 80)

    weights = {}

    rows = soup.select("div[aria-label='Assignment Weights'] tbody tr")

    for row in rows:
        th = row.find("th")
        td = row.find("td")
        if not th or not td:
            continue

        group = th.get_text(strip=True)
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)", td.get_text())

        if match:
            weights[normalize(group)] = float(match.group(1)) / 100.0

    for k, v in weights.items():
        print(f"{k}: {v}")

    # -----------------------------
    # ASSIGNMENTS
    # -----------------------------
    print("\nASSIGNMENTS")
    print("=" * 80)

    rows = soup.select("tr.student_assignment")

    print(f"Found {len(rows)} assignment rows")

    group_scores = defaultdict(lambda: {"earned": 0.0, "possible": 0.0})

    parsed = 0

    for i, row in enumerate(rows, 1):
        title = row.select_one(".title")
        group = row.select_one(".context")
        cell = row.select_one(".assignment_score")

        if not title or not group or not cell:
            continue

        name = title.get_text(" ", strip=True)
        group_name = group.get_text(strip=True)

        earned, possible = extract_score(cell, debug_label=name)

        print(f"\n{name}")
        print(f"  Group: {group_name}")
        print(f"  {earned} / {possible}")

        if earned is None or possible is None:
            print("  ❌ skipped")
            continue

        parsed += 1
        gkey = normalize(group_name)

        group_scores[gkey]["earned"] += earned
        group_scores[gkey]["possible"] += possible

    print(f"\nParsed assignments: {parsed}")

    # -----------------------------
    # GROUP TOTALS
    # -----------------------------
    print("\nGROUP TOTALS")
    print("=" * 80)

    overall = 0.0

    for group, vals in group_scores.items():
        earned = vals["earned"]
        possible = vals["possible"]

        if possible == 0:
            continue

        percent = earned / possible
        weight = weights.get(group, 0.0)

        weighted = percent * weight
        overall += weighted

        print(f"\n{group}")
        print(f"  {earned:.2f} / {possible:.2f}")
        print(f"  {percent:.3%}")
        print(f"  weight: {weight:.2%}")
        print(f"  weighted: {weighted:.3%}")

    # -----------------------------
    # FINAL OUTPUT
    # -----------------------------
    print("\nOVERALL GRADE")
    print("=" * 80)
    print(f"{overall * 100:.2f}%")


# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python calculate_grade.py file.html")
    else:
        main(sys.argv[1])