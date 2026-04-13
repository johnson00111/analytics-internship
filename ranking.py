"""
Opportunity scoring and buyer-persona mapping for non-safety use cases.
"""

import re

import pandas as pd


# ---------------------------------------------------------------------------
# Keyword-based taxonomy (manual refinement over auto-clustering)
# ---------------------------------------------------------------------------
# Auto-clustering by token overlap gets a rough grouping, but misses
# semantic matches and over-merges at lower thresholds.  These keyword
# rules reflect what I saw reading the actual labels.  Each pattern is
# checked in order; first match wins.

NONSAFETY_TAXONOMY = [
    # (category_name, regex pattern applied to label)
    # Order matters — first match wins.  Put more specific patterns first
    # so broad keywords (like "track") don't swallow unrelated items.
    ("Dock & door operations",
     r"dock|door.?(open|duration|close|propp)|turn.?time|trailer.?(pull|detent)|"
     r"cold.?stor|cooler|freezer"),
    ("Food safety & controlled environment",
     r"food.?safe|hair.?net|beard.?net|hygiene|controlled.?env|sanit"),
    ("Security & access control",
     r"security|intrusion|perimeter|license.?plate|unauthorized|after.?hour|"
     r"restricted.?(area|access)|cctv|yard.?gate|carrier.?compliance"),
    ("Operational flow & throughput",
     r"conveyor|congestion|bottleneck|throughput|aisle.?obstruct|pallet.?(flow|stack|build)|"
     r"idle|productivity|dwell|parking.?duration|no.?park|no.?idle|no.?stand|"
     r"machine.?shutdown|vehicle.?idl|staffing|staff.?effic"),
    # Coaching/action before LP — "action tracking" is coaching, not LP
    ("Coaching & action workflow",
     r"action.?(?:track|workflow|manage)|coaching|corrective|accountability|follow.?up|"
     r"assign.?(?:and|incident)|close.?the.?loop|training.?content|clip|video.?for|"
     r"tally|repeat.?offend"),
    ("Loss prevention & damage",
     r"shrink|loss.?prev|product.?(?:damage|condition)|theft|tamper|exonerat|"
     r"mishandl|property.?damage|rack.?(?:collision|impact)"),
    ("Integration & data export",
     r"api|integrat|bi\b|data.?export|external.?system|incident.?manage|"
     r"velocityehs|nvr|vms|legacy"),
    ("ROI & cost justification",
     r"cost|roi\b|claim|premium|business.?case|workers.?comp|injury.?trend|"
     r"value|liabil"),
    ("Analytics & reporting",
     r"dashboard|board|heatmap|heat.?map|analytics|reporting|benchmark|executive|"
     r"trend|gamif|leaderboard|snapshot|notification|email.?summar|digest|"
     r"weekly.?report|monthly.?report"),
    ("Platform & adoption",
     r"role.?based|blurring|privacy|localization|camera.?cover|adoption|onboard|"
     r"trial|pilot|rollout|expansion|renewal|contract|region.?config|"
     r"false.?positive|noise.?reduc|alert.?(volume|noise)|re.?scope"),
    ("Incident investigation",
     r"investigat|evidence.?capture|footage.?retriev|video.?footage|incident.?log|"
     r"historical.?data"),
]

SAFETY_TAXONOMY = [
    ("PIT-pedestrian proximity",
     r"pit.?(?:to.?)?ped|pedestrian.?(?:proximity|interact|detect|monitor)|forklift.?ped"),
    ("PIT-PIT proximity",
     r"pit.?to.?pit|forklift.?to.?forklift"),
    ("Intersection compliance",
     r"intersect|crosswalk|stop.?(?:at|sign|compliance)"),
    ("Ergonomics",
     r"ergonom|improper.?bend|overreach|lifting|posture"),
    ("PPE compliance",
     r"ppe|hard.?hat|vest|glove|hair.?net|beard.?net|high.?vis"),
    ("PIT speeding",
     r"speed(?:ing)?|velocity"),
    ("Spill & floor hazard",
     r"spill|slip|trip|fall|floor.?hazard|wet"),
    ("Restricted zone",
     r"no.?ped|restricted.?zone|no.?pedestrian|area.?control|exclusion"),
    ("Working at heights",
     r"height|harness|ladder|elevated"),
    ("Obstruction & housekeeping",
     r"obstruct|housekeep|egress|blocked|exit|extinguish"),
    ("Dock & loading safety",
     r"dock|trailer|loading|chock|wheel"),
]


def assign_category(label, taxonomy):
    """Match a label against a taxonomy; return category or 'Other'."""
    for cat, pattern in taxonomy:
        if re.search(pattern, label, re.IGNORECASE):
            return cat
    return "Other"


def categorize(df):
    """Add a 'category' column using keyword taxonomy."""
    df = df.copy()
    cats = []
    for _, row in df.iterrows():
        tax = SAFETY_TAXONOMY if row["bucket"] == "safety" else NONSAFETY_TAXONOMY
        cats.append(assign_category(row["label"], tax))
    df["category"] = cats
    return df


# ---------------------------------------------------------------------------
# Opportunity ranking
# ---------------------------------------------------------------------------

def rank_nonsafety(df):
    """
    Rank non-safety categories by three metrics (reported separately,
    no composite score — let the memo make the judgment call).

    Returns a DataFrame with one row per non-safety category.
    """
    ns = df[df["bucket"] == "nonsafety"].copy()

    agg = ns.groupby("category").agg(
        distinct_calls=("file_id", "nunique"),
        total_rows=("label", "count"),
        avg_evidence=("evidence_count", "mean"),
        customer_quotes_sum=("customer_quotes", "sum"),
        total_quotes_sum=("voxel_quotes", lambda x: x.sum() + ns.loc[x.index, "customer_quotes"].sum()),
    ).reset_index()

    # customer voice ratio across the whole category
    agg["customer_voice_ratio"] = (
        agg["customer_quotes_sum"] / agg["total_quotes_sum"].replace(0, 1)
    ).round(2)
    agg["avg_evidence"] = agg["avg_evidence"].round(1)

    agg["confidence"] = agg.apply(_confidence_label, axis=1)
    agg = agg.sort_values("distinct_calls", ascending=False).reset_index(drop=True)
    return agg[["category", "distinct_calls", "total_rows",
                "customer_voice_ratio", "avg_evidence", "confidence"]]


def _confidence_label(row):
    """
    Simple confidence heuristic based on breadth and customer voice.
    Not a model — just a quick read on how much weight to put on each signal.
    """
    if row["distinct_calls"] >= 8 and row["customer_voice_ratio"] >= 0.5:
        return "HIGH"
    if row["distinct_calls"] >= 5:
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# Buyer persona mapping
# ---------------------------------------------------------------------------

_BUYER_MAP = {
    "Dock & door operations": "Facilities / Operations",
    "Food safety & controlled environment": "QA / Compliance",
    "Loss prevention & damage": "LP / Finance",
    "Security & access control": "Facilities / Security",
    "Operational flow & throughput": "Operations",
    "Integration & data export": "IT / Analytics",
    "ROI & cost justification": "Finance / EHS",
    "Coaching & action workflow": "EHS / Safety",
    "Analytics & reporting": "EHS / Leadership",
    "Platform & adoption": "IT / Program Mgmt",
}


def map_buyer(category):
    return _BUYER_MAP.get(category, "—")
