"""
Generates data/sample_reports.csv — a SYNTHETIC DEMONSTRATION DATASET.

The correlations below are deliberately engineered so the pattern-detection
and precursor-signal tools have real, non-random structure to find:

- Assembly Line 3: recurring equipment leakage + wet floors + missing
  signage, concentrated on the night shift, with a rising trend.
- Warehouse B: PPE non-compliance + blocked pathways, fairly steady.
- Loading Zone: forklift/pedestrian proximity issues, spread across shifts.
- Everywhere else: low-level background noise so the "hot" locations
  stand out rather than everything looking equally risky.

This is NOT real incident data. It exists purely to give the demo
something honest to analyze.
"""
import csv
import random
from datetime import date, timedelta

random.seed(42)

LOCATIONS = {
    "Assembly Line 3": {
        "department": "Manufacturing",
        "hazards": [
            ("Equipment leakage", "Near Miss", ["Night", "Night", "Evening"]),
            ("Wet/slippery floor", "Near Miss", ["Night", "Night", "Morning"]),
            ("Missing hazard signage", "Observation", ["Night", "Evening"]),
            ("Machine malfunction", "Incident", ["Night", "Morning"]),
        ],
        "base_count": 34,
        "trend": "increasing",
    },
    "Warehouse B": {
        "department": "Logistics",
        "hazards": [
            ("PPE non-compliance", "Observation", ["Morning", "Evening"]),
            ("Blocked emergency pathway", "Near Miss", ["Morning", "Evening", "Night"]),
            ("Improper storage/stacking", "Observation", ["Morning"]),
        ],
        "base_count": 24,
        "trend": "steady",
    },
    "Loading Zone": {
        "department": "Logistics",
        "hazards": [
            ("Forklift-pedestrian proximity", "Near Miss", ["Morning", "Evening", "Night"]),
            ("Pedestrian crossing violation", "Observation", ["Morning", "Evening"]),
            ("Poor lighting", "Observation", ["Night"]),
        ],
        "base_count": 20,
        "trend": "steady",
    },
    "Packaging Unit": {
        "department": "Manufacturing",
        "hazards": [
            ("PPE non-compliance", "Observation", ["Morning", "Evening"]),
            ("Repetitive strain concern", "Observation", ["Morning"]),
        ],
        "base_count": 11,
        "trend": "steady",
    },
    "Electrical Substation": {
        "department": "Facilities",
        "hazards": [
            ("Electrical hazard", "Near Miss", ["Morning", "Night"]),
            ("Exposed wiring", "Observation", ["Night"]),
        ],
        "base_count": 8,
        "trend": "steady",
    },
    "Main Corridor": {
        "department": "Facilities",
        "hazards": [
            ("Slip/fall hazard", "Observation", ["Morning", "Evening"]),
            ("Blocked fire exit", "Near Miss", ["Evening"]),
        ],
        "base_count": 7,
        "trend": "steady",
    },
}

SEVERITY_BY_TYPE = {"Observation": [1, 2], "Near Miss": [2, 3, 3], "Incident": [3, 4, 5]}

TEMPLATES = {
    "Equipment leakage": [
        "Hydraulic fluid observed leaking from conveyor motor housing near station {n}. Small puddle forming on the floor.",
        "Recurring oil leak from the packaging line gearbox. Maintenance ticket raised but leak returned within days.",
        "Coolant leak detected under the stamping press during {shift} rounds. Area was cordoned but not fully cleaned.",
    ],
    "Wet/slippery floor": [
        "Floor near bay {n} was wet and slippery, likely from the recurring equipment leak. No wet-floor sign present.",
        "Employee nearly slipped on a wet patch close to the conveyor. Surface had not been mopped or marked.",
    ],
    "Missing hazard signage": [
        "Wet floor / hazard signage was missing near the leak-prone section of the line during {shift} shift.",
        "No caution signage posted around the ongoing maintenance work, despite repeated requests from the {shift} crew.",
    ],
    "Machine malfunction": [
        "Conveyor belt motor made unusual grinding noise and stalled briefly before restarting on its own.",
        "Press machine safety interlock did not engage properly on first attempt; operator had to reset it manually.",
    ],
    "PPE non-compliance": [
        "Two workers observed without safety goggles while handling packaging materials near bay {n}.",
        "Forklift operator noted operating without a high-visibility vest during {shift} shift.",
    ],
    "Blocked emergency pathway": [
        "Pallets stacked partially blocking the marked emergency exit route near dock {n}.",
        "Emergency pathway near the loading dock was obstructed by returned stock awaiting pickup.",
    ],
    "Improper storage/stacking": [
        "Boxes stacked above the marked height limit on rack {n}, creating a potential fall/collapse risk.",
    ],
    "Forklift-pedestrian proximity": [
        "Forklift came within close proximity of a pedestrian walkway with no spotter present near dock {n}.",
        "Near miss between reversing forklift and warehouse staff crossing an unmarked pedestrian lane.",
    ],
    "Pedestrian crossing violation": [
        "Pedestrian crossed through an active vehicle lane instead of using the marked crossing near dock {n}.",
    ],
    "Poor lighting": [
        "Loading zone lighting was noticeably dim during {shift} shift, making it hard to see approaching vehicles.",
    ],
    "Repetitive strain concern": [
        "Packaging staff reported wrist discomfort after extended repetitive sealing tasks without rotation.",
    ],
    "Electrical hazard": [
        "Panel door on substation unit {n} was left open with live components partially accessible.",
    ],
    "Exposed wiring": [
        "Exposed wiring noticed near the substation junction box, insulation appeared worn.",
    ],
    "Slip/fall hazard": [
        "Loose floor tile near the main corridor created a trip hazard close to the stairwell.",
    ],
    "Blocked fire exit": [
        "Fire exit near the main corridor was found propped with storage boxes during the {shift} check.",
    ],
}

START_DATE = date(2026, 6, 1)
END_DATE = date(2026, 9, 15)
TOTAL_DAYS = (END_DATE - START_DATE).days


def weighted_day(trend: str) -> date:
    """Pick a report date, skewed toward recent dates for 'increasing' trend."""
    if trend == "increasing":
        r = random.random() ** 0.4  # sqrt-like skew toward 1.0 (recent dates)
    else:
        r = random.random()
    offset = int(r * TOTAL_DAYS)
    return START_DATE + timedelta(days=offset)


def make_report(idx: int, location: str, info: dict) -> dict:
    hazard, report_type, shifts = random.choice(info["hazards"])
    shift = random.choice(shifts)
    severity = random.choice(SEVERITY_BY_TYPE[report_type])
    template = random.choice(TEMPLATES.get(hazard, ["{location} safety observation logged."]))
    text = template.format(n=random.randint(1, 9), shift=shift.lower(), location=location)
    d = weighted_day(info["trend"])
    return {
        "report_id": f"SR-{1000 + idx}",
        "date": d.isoformat(),
        "location": location,
        "department": info["department"],
        "shift": shift,
        "report_type": report_type,
        "severity": severity,
        "hazard": hazard,
        "description": text,
    }


def generate(path: str) -> None:
    rows = []
    idx = 0
    for location, info in LOCATIONS.items():
        for _ in range(info["base_count"]):
            rows.append(make_report(idx, location, info))
            idx += 1
    random.shuffle(rows)
    rows.sort(key=lambda r: r["date"])
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "report_id", "date", "location", "department", "shift",
                "report_type", "severity", "hazard", "description",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} synthetic reports to {path}")


if __name__ == "__main__":
    generate("sample_reports.csv")
