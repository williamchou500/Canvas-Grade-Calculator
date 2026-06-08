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


def normalize_weights(weights):
    """Return usable weights or None if missing/unusable."""
    vals = list(weights.values())

    if len(vals) == 0:
        return None

    # if everything is basically zero → treat as no weights
    if sum(vals) < 0.01:
        return None

    return weights


# -----------------------------
# Score extraction
# -----------------------------
def extract_possible(full_text, cell):
    # 1. Standard "/ X"
    match = re.search(r"/\s*([0-9]+(?:\.[0-9]+)?)", full_text)
    if match:
        return float(match.group(1))

    # 2. "out of X"
    match = re.search(r"out of\s*([0-9]+(?:\.[0-9]+)?)", full_text, re.I)
    if match:
        return float(match.group(1))

    # 3. Percent-based fallback
    perc_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", full_text)
    if perc_match:
        percent = float(perc_match.group(1))

        hidden = cell.select_one(".original_score")
        if hidden:
            earned = parse_float(hidden.get_text(strip=True))
            if earned is not None and percent > 0:
                return earned / (percent / 100.0)

        return 100.0

    # 4. FINAL SAFETY NET (prevents dropping finals)
    if "%" in full_text:
        return 100.0

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
    # possible
    # -------------------------
    possible = extract_possible(full_text, cell)

    if earned is not None and possible is None:
        if "%" in full_text:
            possible = 100.0

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

    for row in rows:
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

        if earned is None:
            print("  ❌ skipped (no earned score)")
            continue

        if possible is None:
            print("  ⚠️ fixing missing possible → assuming 100")
            possible = 100.0

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

    usable_weights = normalize_weights(weights)

    if usable_weights is None:
        # =========================
        # TRUE POINTS-BASED MODE
        # =========================
        print("\n⚠️ No valid weights detected → using TOTAL POINTS mode\n")

        total_earned = 0.0
        total_possible = 0.0

        for group, vals in group_scores.items():
            if vals["possible"] > 0:
                total_earned += vals["earned"]
                total_possible += vals["possible"]

        if total_possible == 0:
            overall = 0.0
        else:
            overall = total_earned / total_possible

        print(f"TOTAL EARNED: {total_earned:.2f}")
        print(f"TOTAL POSSIBLE: {total_possible:.2f}")
        print(f"OVERALL: {overall:.3%}")

    else:
        # =========================
        # WEIGHTED MODE
        # =========================
        overall = 0.0

        for group, vals in group_scores.items():
            earned = vals["earned"]
            possible = vals["possible"]

            if possible == 0:
                continue

            percent = earned / possible
            weight = usable_weights.get(group, 0.0)

            weighted = percent * weight
            overall += weighted

            print(f"\n{group}")
            print(f"  {earned:.2f} / {possible:.2f}")
            print(f"  {percent:.3%}")
            print(f"  weight: {weight:.2%}")
            print(f"  weighted: {weighted:.3%}")

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