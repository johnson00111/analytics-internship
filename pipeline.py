"""
Data loading, label normalization, and quality checks for Voxel
extraction output analysis.
"""

import json
import os
import re
from collections import defaultdict

import pandas as pd


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_all(data_dir="safety-nonsafety"):
    """Load every JSON file into a flat DataFrame (one row per use case)."""
    rows = []
    empty_files = []

    for fname in sorted(os.listdir(data_dir)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(data_dir, fname)
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)

        file_id = fname.replace(".json", "")
        title = doc.get("meeting_title", "")
        start = doc.get("start_time", "")
        ext = doc.get("extraction", {})

        safety = ext.get("safety_use_cases", [])
        nonsafety = ext.get("nonsafety_use_cases", [])

        if not safety and not nonsafety:
            empty_files.append(file_id)
            continue

        for bucket, items in [("safety", safety), ("nonsafety", nonsafety)]:
            for uc in items:
                speakers = [e.get("speaker", "") for e in uc.get("evidence", [])]
                quotes = [e.get("quote", "") for e in uc.get("evidence", [])]
                rows.append({
                    "file_id": file_id,
                    "meeting_title": title,
                    "company": _parse_company(title),
                    "start_time": start,
                    "bucket": bucket,
                    "label": uc.get("label", ""),
                    "description": uc.get("description", ""),
                    "evidence_count": len(uc.get("evidence", [])),
                    "speakers": speakers,
                    "quotes": quotes,
                })

    df = pd.DataFrame(rows)
    if "start_time" in df.columns:
        df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
    return df, empty_files


_SEPARATORS = re.compile(r"\s*(?://|<>|\||\+|/|–|—)\s*")
_VOXEL = re.compile(r"^voxel(?:\s+ai)?$", re.IGNORECASE)
_PREFIX = re.compile(r"^\(ext\)\s*|^FW:\s*", re.IGNORECASE)


def _parse_company(title):
    """Best-effort extraction of customer company name from meeting title."""
    title = _PREFIX.sub("", title).strip()
    parts = _SEPARATORS.split(title)
    # grab every segment that isn't just "Voxel" / "Voxel AI"
    candidates = [p.strip() for p in parts if not _VOXEL.match(p.strip())]
    if candidates:
        # take the first non-Voxel chunk and trim common suffixes
        name = candidates[0]
        name = re.sub(r"\s*[-:]\s*(Bi-Weekly|Monthly|Sync|Training|Intro|Check-?in|"
                       r"Demo|Call|Discussion|Reconnect|Deployment|Kickoff|Overview|"
                       r"Discovery|Review).*$", "", name, flags=re.IGNORECASE)
        return name.strip() or title
    return title


# ---------------------------------------------------------------------------
# Label normalization (Jaccard similarity clustering)
# ---------------------------------------------------------------------------

_STOPWORDS = frozenset(
    "a an the and or for to in of on at by is with from via as this that "
    "be are was were been has have had do does did will can could should "
    "would may might shall into not no nor".split()
)


def tokenize(label):
    """Lowercase a label, strip punctuation, drop stopwords."""
    words = re.findall(r"[a-z0-9]+", label.lower())
    return frozenset(w for w in words if w not in _STOPWORDS)


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def auto_cluster(labels, threshold=0.4):
    """
    Single-linkage clustering based on Jaccard token overlap.

    Returns a dict mapping each original label to a representative
    (the shortest label in its cluster, as a rough canonical name).
    This is a rough first pass -- review and correct by hand.
    """
    token_sets = {lab: tokenize(lab) for lab in labels}
    unique = list(set(labels))
    parent = {lab: lab for lab in unique}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(len(unique)):
        for j in range(i + 1, len(unique)):
            if jaccard(token_sets[unique[i]], token_sets[unique[j]]) >= threshold:
                union(unique[i], unique[j])

    clusters = defaultdict(list)
    for lab in unique:
        clusters[find(lab)].append(lab)

    # pick the shortest label as the cluster representative
    mapping = {}
    for members in clusters.values():
        rep = min(members, key=len)
        for m in members:
            mapping[m] = rep
    return mapping



# ---------------------------------------------------------------------------
# Quality checks
# ---------------------------------------------------------------------------

def classify_speaker(speaker_str):
    """'voxel' if the email domain is voxelai.com, else 'customer'."""
    if "voxelai.com" in speaker_str.lower():
        return "voxel"
    return "customer"


def add_voice_mix(df):
    """
    For each row, compute how many evidence quotes come from a customer
    vs. a Voxel speaker.  Adds customer_quotes, voxel_quotes, voice_ratio.
    """
    df = df.copy()
    cust, vox = [], []
    for speakers in df["speakers"]:
        roles = [classify_speaker(s) for s in speakers]
        cust.append(roles.count("customer"))
        vox.append(roles.count("voxel"))
    df["customer_quotes"] = cust
    df["voxel_quotes"] = vox
    total = df["customer_quotes"] + df["voxel_quotes"]
    df["voice_ratio"] = (df["customer_quotes"] / total.replace(0, 1)).round(2)
    return df


def cross_bucket_labels(df):
    """Find file_ids where the exact same label appears in both buckets."""
    safety = df[df["bucket"] == "safety"][["file_id", "label"]]
    nonsafety = df[df["bucket"] == "nonsafety"][["file_id", "label"]]
    overlap = safety.merge(nonsafety, on=["file_id", "label"])
    return overlap.drop_duplicates()


def cross_bucket_quotes(df):
    """Find evidence quotes that appear under both buckets in the same file."""
    records = []
    for fid, group in df.groupby("file_id"):
        s_quotes = set()
        n_quotes = set()
        for _, row in group.iterrows():
            target = s_quotes if row["bucket"] == "safety" else n_quotes
            for q in row["quotes"]:
                target.add(q.strip().lower()[:80])  # first 80 chars
        shared = s_quotes & n_quotes
        if shared:
            records.append({"file_id": fid, "shared_quote_count": len(shared)})
    return pd.DataFrame(records)


_PLATFORM_KEYWORDS = re.compile(
    r"workflow|dashboard|board|notification|role.?based|gamif|blurring|"
    r"localization|subscription|export|email summar|report subscri",
    re.IGNORECASE,
)


def flag_platform_items(df):
    """
    Mark rows that look like Voxel platform features, not customer needs.

    Keyword match alone isn't enough -- a customer asking "can we get a
    board for X?" is real demand.  Only flag when keyword matches AND
    all evidence speakers are Voxel.
    """
    df = df.copy()
    kw_match = df["label"].str.contains(_PLATFORM_KEYWORDS, na=False)
    voxel_only = df["customer_quotes"] == 0
    df["is_platform_item"] = kw_match & voxel_only
    return df


def flag_weak_evidence(df):
    """Flag rows where evidence is thin: 1 quote and it's short."""
    df = df.copy()
    short_quote = df["quotes"].apply(
        lambda qs: len(qs) == 1 and len(qs[0]) < 50 if qs else True
    )
    df["weak_evidence"] = (df["evidence_count"] <= 1) & short_quote
    return df
