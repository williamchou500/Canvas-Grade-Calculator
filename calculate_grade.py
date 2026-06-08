from bs4 import BeautifulSoup
from dataclasses import dataclass
from collections import defaultdict
import re
import sys


@dataclass
class Assignment:
    name: str
    earned: float
    possible: float
    group: str | None = None


def load_html(path):
    with open(path, "r", encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "html.parser")


def parse_score(text):
    """
    Converts strings like:
    '95 / 100'
    '17.5/20'

    into:
    (95.0, 100.0)
    """

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
        text
    )

    if not match:
        raise ValueError(f"No score found in: {text}")

    return (
        float(match.group(1)),
        float(match.group(2))
    )


def extract_assignments(soup):
    """
    Generic table parser.

    You may need to adjust selectors depending
    on your Canvas HTML.
    """

    assignments = []

    rows = soup.find_all("tr")

    for row in rows:

        row_text = row.get_text(" ", strip=True)

        try:
            earned, possible = parse_score(row_text)
        except ValueError:
            continue

        cells = row.find_all(["td", "th"])

        if len(cells) == 0:
            continue

        name = cells[0].get_text(strip=True)

        group = None

        if len(cells) >= 3:
            group = cells[2].get_text(strip=True)

        assignments.append(
            Assignment(
                name=name,
                earned=earned,
                possible=possible,
                group=group
            )
        )

    return assignments


def extract_weights(soup):
    """
    Attempts to find category weights.

    Looks for patterns like:
    Homework 20%
    Exams 50%

    Returns:
    {
        "Homework": 20.0,
        "Exams": 50.0
    }
    """

    weights = {}

    text = soup.get_text("\n", strip=True)

    pattern = re.compile(
        r"([A-Za-z][A-Za-z\s]+?)\s+(\d+(?:\.\d+)?)%"
    )

    for match in pattern.finditer(text):
        category = match.group(1).strip()
        weight = float(match.group(2))

        if 0 < weight <= 100:
            weights[category] = weight

    return weights


def calculate_point_grade(assignments):
    earned = sum(a.earned for a in assignments)
    possible = sum(a.possible for a in assignments)

    if possible == 0:
        return 0

    return earned / possible


def calculate_weighted_grade(assignments, weights):
    groups = defaultdict(list)

    for a in assignments:
        if a.group:
            groups[a.group].append(a)

    weighted_total = 0
    used_weight = 0

    for group_name, weight in weights.items():

        group_assignments = groups.get(group_name)

        if not group_assignments:
            continue

        earned = sum(a.earned for a in group_assignments)
        possible = sum(a.possible for a in group_assignments)

        if possible == 0:
            continue

        percentage = earned / possible

        weighted_total += percentage * weight
        used_weight += weight

    if used_weight == 0:
        return calculate_point_grade(assignments)

    return weighted_total / used_weight


def print_assignments(assignments):
    print("\nAssignments")
    print("-" * 60)

    for a in assignments:
        print(
            f"{a.name:<30} "
            f"{a.earned:>6.1f}/{a.possible:<6.1f} "
            f"{a.group or 'Ungrouped'}"
        )


def main():

    if len(sys.argv) != 2:
        print(
            "Usage:\n"
            "python canvas_grade_calculator.py grades.html"
        )
        return

    html_file = sys.argv[1]

    soup = load_html(html_file)

    assignments = extract_assignments(soup)

    if not assignments:
        print("No assignments found.")
        return

    weights = extract_weights(soup)

    print_assignments(assignments)

    print("\nDetected Weights")
    print("-" * 60)

    if weights:
        for group, weight in weights.items():
            print(f"{group}: {weight}%")

        grade = calculate_weighted_grade(
            assignments,
            weights
        )

        print(
            f"\nWeighted Grade: {grade * 100:.2f}%"
        )

    else:
        grade = calculate_point_grade(assignments)

        print(
            "\nNo assignment weights detected."
        )
        print(
            f"Point-Based Grade: {grade * 100:.2f}%"
        )


if __name__ == "__main__":
    main()