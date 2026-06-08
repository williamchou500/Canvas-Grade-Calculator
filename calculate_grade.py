from bs4 import BeautifulSoup
from dataclasses import dataclass
from collections import defaultdict
import re
import sys


@dataclass
class Assignment:
    name: str
    group: str
    earned: float
    possible: float


def load_html(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return BeautifulSoup(f, "html.parser")


def extract_assignments(soup):
    assignments = []

    rows = soup.select("tr.student_assignment")

    for row in rows:

        title_cell = row.select_one("th.title")
        if not title_cell:
            continue

        name_link = title_cell.select_one("a")
        context_div = title_cell.select_one(".context")

        name = (
            name_link.get_text(strip=True)
            if name_link
            else "Unknown Assignment"
        )

        group = (
            context_div.get_text(strip=True)
            if context_div
            else "Uncategorized"
        )

        score_cell = row.select_one("td.assignment_score")
        if not score_cell:
            continue

        grade_span = score_cell.select_one("span.grade")
        if not grade_span:
            continue

        try:
            earned = float(grade_span.get_text(strip=True))
        except ValueError:
            continue

        score_text = score_cell.get_text(" ", strip=True)

        possible_match = re.search(
            r"/\s*(\d+(?:\.\d+)?)",
            score_text
        )

        if not possible_match:
            continue

        possible = float(possible_match.group(1))

        assignments.append(
            Assignment(
                name=name,
                group=group,
                earned=earned,
                possible=possible
            )
        )

    return assignments


def extract_weights(soup):
    weights = {}

    header = soup.find("h2", string=re.compile(
        "Assignments are weighted by group",
        re.I
    ))

    if not header:
        return weights

    table = header.find_next("table")

    if not table:
        return weights

    rows = table.select("tbody tr")

    for row in rows:

        group_cell = row.find("th")
        weight_cell = row.find("td")

        if not group_cell or not weight_cell:
            continue

        group = group_cell.get_text(strip=True)

        if group.lower() == "total":
            continue

        weight_text = weight_cell.get_text(strip=True)

        match = re.search(
            r"(\d+(?:\.\d+)?)%",
            weight_text
        )

        if not match:
            continue

        weight = float(match.group(1))

        weights[group] = weight

    return weights


def calculate_group_grades(assignments):
    groups = defaultdict(
        lambda: {"earned": 0, "possible": 0}
    )

    for a in assignments:
        groups[a.group]["earned"] += a.earned
        groups[a.group]["possible"] += a.possible

    results = {}

    for group, data in groups.items():

        if data["possible"] == 0:
            continue

        results[group] = (
            data["earned"] /
            data["possible"]
        )

    return results


def calculate_weighted_grade(group_grades, weights):
    total = 0

    for group, weight in weights.items():

        if weight == 0:
            continue

        if group not in group_grades:
            continue

        total += (
            group_grades[group]
            * weight
        )

    return total / 100


def print_report(assignments, weights):
    print("\nASSIGNMENTS")
    print("=" * 80)

    for a in assignments:
        print(
            f"{a.name}\n"
            f"  Group: {a.group}\n"
            f"  Score: {a.earned}/{a.possible}\n"
        )

    group_grades = calculate_group_grades(assignments)

    print("\nGROUP TOTALS")
    print("=" * 80)

    for group, pct in sorted(group_grades.items()):

        weight = weights.get(group, 0)

        print(
            f"{group:<40}"
            f"{pct*100:>7.2f}%"
            f"   weight={weight}%"
        )

    overall = calculate_weighted_grade(
        group_grades,
        weights
    )

    print("\nOVERALL GRADE")
    print("=" * 80)
    print(f"{overall*100:.2f}%")

    return overall


def main():
    if len(sys.argv) != 2:
        print(
            "Usage:\n"
            "python canvas_grade_calculator.py grades.html"
        )
        return

    soup = load_html(sys.argv[1])

    assignments = extract_assignments(soup)
    weights = extract_weights(soup)

    print_report(assignments, weights)


if __name__ == "__main__":
    main()