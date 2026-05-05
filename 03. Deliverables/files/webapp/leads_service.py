"""Leads loader: reads lead_scores_output.csv once, exposes filter / paginate / export."""
import io
from pathlib import Path
from typing import Optional

import pandas as pd

CSV_PATH = Path(__file__).parent.parent / "lead_scores_output.csv"

_CACHE: Optional[pd.DataFrame] = None


def load_leads() -> pd.DataFrame:
    global _CACHE
    if _CACHE is None:
        df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
        df.columns = [c.strip() for c in df.columns]
        _CACHE = df
    return _CACHE


def reference_values():
    """Return distinct filter values for the UI."""
    df = load_leads()
    return {
        "regions": sorted([str(x) for x in df["Region"].dropna().unique() if str(x).strip()]),
        "levels": sorted([str(x) for x in df["study_level"].dropna().unique() if str(x).strip()]),
        "domains": sorted([str(x) for x in df["domaine_etude"].dropna().unique() if str(x).strip()]),
        "classes": ["A", "B", "C"],
    }


def kpis_for_user(quota_leads: int, consumed_total: int):
    df = load_leads()
    optin = df[df["optin_commercial_actuel"] == True]  # noqa: E712
    by_class = optin.groupby("lead_class").size().to_dict()
    return {
        "available_total": len(optin),
        "available_a": int(by_class.get("A", 0)),
        "available_b": int(by_class.get("B", 0)),
        "available_c": int(by_class.get("C", 0)),
        "quota": quota_leads,
        "consumed": consumed_total,
        "remaining": max(0, quota_leads - consumed_total),
        "quota_pct": min(100, round(consumed_total / quota_leads * 100, 1)) if quota_leads else 0,
    }


def filter_leads(region=None, level=None, domain=None, lead_class=None,
                 score_min=0, optin_only=True, limit_id=None) -> pd.DataFrame:
    df = load_leads()
    if optin_only:
        df = df[df["optin_commercial_actuel"] == True]  # noqa: E712
    if region and region != "all":
        df = df[df["Region"] == region]
    if level and level != "all":
        df = df[df["study_level"] == level]
    if domain and domain != "all":
        df = df[df["domaine_etude"] == domain]
    if lead_class and lead_class != "all":
        df = df[df["lead_class"] == lead_class]
    try:
        score_min = int(score_min or 0)
    except ValueError:
        score_min = 0
    if score_min > 0:
        df = df[df["score_total"] >= score_min]
    if limit_id:
        df = df[df["id_Inscrit_site"].astype(str).str.contains(str(limit_id))]
    return df.sort_values("score_total", ascending=False)


def paginate(df: pd.DataFrame, page: int = 1, per_page: int = 50):
    total = len(df)
    page = max(1, page)
    pages = max(1, (total + per_page - 1) // per_page)
    start = (page - 1) * per_page
    end = start + per_page
    return df.iloc[start:end], total, pages


def to_export_csv(df: pd.DataFrame) -> bytes:
    """Return CSV bytes — RGPD-safe: only optin contacts, anonymized cols only."""
    safe_cols = [
        "id_Inscrit_site", "study_level", "domaine_etude", "profile",
        "Region", "Departement",
        "score_fraicheur", "score_intention", "score_engagement", "score_total",
        "lead_class",
        "a_visite_salon", "est_venu_salon", "nb_salons",
        "nb_emails_ouverts", "nb_emails_cliques",
        "a_utilise_agent", "nb_conversations",
        "Proba_CSP_Plus", "Proba_CSP_Moins", "ACTIF",
    ]
    cols = [c for c in safe_cols if c in df.columns]
    buf = io.BytesIO()
    df[cols].to_csv(buf, index=False, encoding="utf-8-sig")
    buf.seek(0)
    return buf.read()


def class_counts(df: pd.DataFrame) -> dict:
    return df["lead_class"].value_counts().to_dict() if "lead_class" in df.columns else {}
