import re
from bs4 import BeautifulSoup
from collections import defaultdict


def parse_float(text):
    if text is None:
        return None
    text = text.strip()
    try:
        return float(text)
    except:
        return None


def extract_score(cell):
    """
    Correctly extracts:
      earned = visible grade (span.original_score or span.grade)
      possible = denominator from '/ X'
    """

    # --- FULL TEXT DEBUG ---
    full_text = cell.get_text(" ", strip=True)

    # 1. Earned score (best source: original_score or visible grade)
    earned_tag = cell.select_one(".original_score") or cell.select_one(".grade")

    earned = parse_float(earned_tag.get_text(strip=True)) if earned_tag else None

    # 2. Possible points → MUST come from "/ X"
    match = re.search(r"/\s*([0-9]+(?:\.[0-9]+)?)", full_text)
    possible = parse_float(match.group(1)) if match else None

    # DEBUG per assignment
    if earned is None or possible is None:
        print("\nPARSE DEBUG")
        print("TEXT:", full_text)
        print("EARNED:", earned)
        print("POSSIBLE:", possible)

    return earned, possible


def main(file_path):
    print("\nLOADING FILE")
    print("=" * 80)
    print(file_path)

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    # --- WEIGHT TABLE ---
    weights = {}
    print("\nWEIGHT DEBUG")
    print("=" * 80)

    weight_rows = soup.select("div[aria-label='Assignment Weights'] tbody tr")

    for row in weight_rows:
        cols = row.find_all("td")
        th = row.find("th")
        if not th or len(cols) < 1:
            continue

        group = th.get_text(strip=True)
        weight_text = cols[0].get_text(strip=True)

        match = re.search(r"([0-9.]+)", weight_text)
        if match:
            weights[group] = float(match.group(1)) / 100.0

    print(f"Total weights loaded: {len(weights)}")
    for k, v in weights.items():
        print(f"  {k}: {v}")

    # --- ASSIGNMENTS ---
    print("\nASSIGNMENTS")
    print("=" * 80)

    rows = soup.select("tr.student_assignment")

    print(f"Found {len(rows)} assignment rows")

    group_scores = defaultdict(lambda: {"earned": 0.0, "possible": 0.0})

    parsed_count = 0

    for i, row in enumerate(rows, 1):
        title = row.select_one(".title")
        group = row.select_one(".context")
        score_cell = row.select_one(".assignment_score")

        if not title or not group or not score_cell:
            continue

        name = title.get_text(" ", strip=True)
        group_name = group.get_text(strip=True)

        earned, possible = extract_score(score_cell)

        print(f"\nAssignment #{i}")
        print("  Name:", name)
        print("  Group:", group_name)
        print("  Earned:", earned)
        print("  Possible:", possible)

        if earned is None or possible is None:
            print("  ❌ Skipped (parse failure)")
            continue

        parsed_count += 1
        group_scores[group_name]["earned"] += earned
        group_scores[group_name]["possible"] += possible

    print(f"\nParsed assignments: {parsed_count}")

    # --- GROUP TOTALS ---
    print("\nGROUP TOTALS")
    print("=" * 80)

    overall = 0.0

    for group, vals in group_scores.items():
        earned = vals["earned"]
        possible = vals["possible"]

        if possible == 0:
            continue

        percent = earned / possible
        weight = weights.get(group, 0)

        weighted = percent * weight
        overall += weighted

        print(f"{group}")
        print(f"  Score: {earned:.2f}/{possible:.2f}")
        print(f"  Percent: {percent:.4f}")
        print(f"  Weight: {weight:.2f}")
        print(f"  Weighted: {weighted:.4f}")

    # --- OVERALL ---
    print("\nOVERALL GRADE")
    print("=" * 80)
    print(f"{overall * 100:.2f}%")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python calculate_grade.py <file.html>")
    else:
        main(sys.argv[1])