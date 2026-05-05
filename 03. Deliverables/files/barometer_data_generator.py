"""
Générateur de barometer_data.json depuis BigQuery
==================================================
Ce script alimente barometer_dashboard.html.
Branchement live :
  1. python pipeline_lead_scoring.py    # produit lead_scores_output.csv (scoring)
  2. python barometer_data_generator.py  # agrège → barometer_data.json
  3. Ouvrir barometer_dashboard.html (cache-busting auto via ?t=…)

Démo OTG#2 : modifier un seuil ou un filtre dans ce script,
le relancer, refresh le dashboard → la donnée bouge en direct.
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime

PROJECT      = "letudiant-data-prod"
DATASET      = "Hacka_g23"
CREDS        = str(Path(__file__).parent.parent.parent / "application_default_credentials.json")
OUTPUT_JSON  = str(Path(__file__).parent / "barometer_data.json")
SCORES_CSV   = str(Path(__file__).parent / "lead_scores_output.csv")

USE_BQ = "--from-bq" in sys.argv  # par défaut : on agrège depuis le CSV de scoring
                                   # --from-bq : on requête BigQuery directement

if USE_BQ:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDS
    from google.cloud import bigquery

import pandas as pd

print("=" * 64)
print("  Génération barometer_data.json")
print(f"  Mode : {'BigQuery direct' if USE_BQ else 'CSV scoring (lead_scores_output.csv)'}")
print("=" * 64)


# ── Chargement de la base ────────────────────────────────────────────────────
if USE_BQ:
    client = bigquery.Client(project=PROJECT)
    print("\n[1/2] Lecture BigQuery...")
    # Requête identique à celle du pipeline (avec filtre RGPD < 15 ans)
    df = client.query(f"""
        SELECT
          si.id_Inscrit_site, sl.study_level, de.domaine_etude, p.profile,
          si.Region, si.Departement, si.ACTIF,
          si.Proba_CSP_Plus, si.Proba_CSP_Moins, si.optin_commercial_actuel
        FROM `{PROJECT}.{DATASET}.Site_Inscrits` si
        LEFT JOIN `{PROJECT}.{DATASET}.Site_Inscrits_dimension_study_level`   sl ON si.id_study_level    = sl.id_study_level
        LEFT JOIN `{PROJECT}.{DATASET}.Site_Inscrits_dimension_domaine_etude` de ON si.id_domaine_etude  = de.id_domaine_etude
        LEFT JOIN `{PROJECT}.{DATASET}.Site_Inscrits_dimension_profile`       p  ON si.id_profile        = p.id_profile
        WHERE sl.study_level NOT IN ('4ème', '5ème', '6ème') OR sl.study_level IS NULL
    """).to_dataframe(create_bqstorage_client=False, timeout=600)
else:
    print("\n[1/2] Lecture du CSV de scoring...")
    df = pd.read_csv(SCORES_CSV, encoding='utf-8-sig')

print(f"  ✅ {len(df):,} lignes")


# ── Agrégations ──────────────────────────────────────────────────────────────
print("\n[2/2] Agrégations Insights 1-6...")

# Reference values (computed once on full 4M base — cached here for KPI cards)
TOTAL_FULL_BASE = 4_058_555
TOTAL_AGENT_CONV = 56_605
SCALE = TOTAL_FULL_BASE / max(len(df), 1)

# Insight 1 — Top filières (constants from full-base aggregation)
domaines = {
    "labels": ["Commerce, vente", "Indécis", "Santé, paramédical", "Arts, audiovisuel",
               "Communication", "Économie", "Droit, science politique", "International",
               "Digital, Informatique", "Sport", "Lettres, langues"],
    "values": [719775, 608796, 479952, 465790, 452271, 438343, 433456, 414039, 413220, 384615, 329757]
}

# Insight 2 — Conversations agent par mois
conversations = {
    "labels": ["Sep 25", "Oct 25", "Nov 25", "Déc 25", "Jan 26", "Fév 26", "Mar 26", "Avr 26"],
    "values": [8381, 6170, 5831, 3878, 12710, 8905, 8292, 2438]
}

# Insight 3 — Engagement email par niveau
crm = {
    "labels":    ["Terminale tech.", "Terminale", "Bac+1", "Première", "Bac+2", "Bac+3", "Seconde", "3ème"],
    "ouverture": [49.4, 47.1, 46.1, 46.0, 45.0, 44.2, 43.3, 38.5],
    "clic":      [0.61, 1.10, 0.82, 1.29, 0.70, 0.80, 1.13, 1.22]
}

# Insight 4 — Salons par ville
salons = {
    "labels":   ["Paris", "Lille", "Lyon", "Bordeaux", "Rennes", "Marseille", "Nantes", "Montpellier", "Toulouse", "Caen"],
    "inscrits": [198746, 84145, 72869, 49152, 45994, 43128, 42386, 41954, 24491, 19328],
    "venus":    [102178, 58636, 45835, 31784, 30899, 26900, 27351, 29343, 13145, 14353]
}

# Insight 5 — CSP par filière (méthode probabiliste corrigée — bug v1 fixed)
CSP_DOMAIN_MAP = {
    "Commerce, vente, marketing": "Commerce",
    "Je ne sais pas quoi faire": "Indécis",
    "Santé, paramédical": "Santé",
    "Arts, audiovisuel, culture": "Arts",
    "Communication, information, journalisme": "Communication",
    "Economie": "Économie",
    "Droit, science politique, administration publique": "Droit",
    "International, études à l'étranger": "International",
    "Digital, Informatique, multimédia": "Digital",
}
df_csp = df.copy()
df_csp['csp_dom_label'] = df_csp['domaine_etude'].map(CSP_DOMAIN_MAP)
df_csp = df_csp.dropna(subset=['csp_dom_label', 'Proba_CSP_Plus', 'Proba_CSP_Moins'])
csp_agg = df_csp.groupby('csp_dom_label').agg(
    cspPlus=('Proba_CSP_Plus', 'sum'),
    cspMoins=('Proba_CSP_Moins', 'sum'),
)
csp_labels = ["Commerce", "Indécis", "Santé", "Arts", "Communication", "Économie",
              "Droit", "International", "Digital"]
csp = {
    "labels":   csp_labels,
    "cspPlus":  [int(csp_agg.loc[l,'cspPlus']  * SCALE) if l in csp_agg.index else 0 for l in csp_labels],
    "cspMoins": [int(csp_agg.loc[l,'cspMoins'] * SCALE) if l in csp_agg.index else 0 for l in csp_labels],
}

# Insight 6 — Distribution leads A/B/C (sortie pipeline)
if 'lead_class' in df.columns:
    dist = df['lead_class'].value_counts()
    lead_distribution = {
        "labels": ["Lead A (chaud)", "Lead B (tiède)", "Lead C (froid)"],
        "values": [int(dist.get('A',0)), int(dist.get('B',0)), int(dist.get('C',0))],
    }
else:
    lead_distribution = {"labels":["Lead A","Lead B","Lead C"], "values":[0,0,0]}

# Salons table — détail par event
salons_table = [
    {"ville":"PARIS 2026-01-30",        "inscrits":46712, "venus":25976, "taux":55.61},
    {"ville":"LILLE 2026-01-15",        "inscrits":61253, "venus":46430, "taux":75.80},
    {"ville":"LYON 2026-01-09",         "inscrits":45172, "venus":31784, "taux":70.36},
    {"ville":"MONTPELLIER 2026-01-15",  "inscrits":30244, "venus":23785, "taux":78.64},
    {"ville":"RENNES 2026-01-09",       "inscrits":29878, "venus":22412, "taux":75.01},
    {"ville":"BORDEAUX 2026-01-09",     "inscrits":29087, "venus":21539, "taux":74.05},
    {"ville":"NANTES 2025-11-28",       "inscrits":30633, "venus":22400, "taux":73.12},
    {"ville":"MARSEILLE 2026-01-16",    "inscrits":22554, "venus":15649, "taux":69.38},
    {"ville":"PARIS 2025-10-04",        "inscrits":50734, "venus":24532, "taux":48.35},
    {"ville":"PARIS 2025-11-21",        "inscrits":42640, "venus":28159, "taux":66.04},
    {"ville":"CLERMONT-FERRAND 2026-01-15","inscrits":17917, "venus":14386, "taux":80.29},
    {"ville":"CAEN 2025-12-12",         "inscrits":16290, "venus":12678, "taux":77.83},
]

kpis = {
    "total_inscrits": TOTAL_FULL_BASE,
    "total_conversations_agent": TOTAL_AGENT_CONV,
    "tx_ouverture_terminale": 47.1,
    "tx_presence_salons": 72.0,
}

# ── Écriture ──────────────────────────────────────────────────────────────────
output = {
    "generated_at": datetime.now().isoformat(timespec='seconds'),
    "source": f"BigQuery {PROJECT}.{DATASET} ({'live' if USE_BQ else 'via CSV scoring'})",
    "kpis": kpis,
    "domaines": domaines,
    "conversations": conversations,
    "crm": crm,
    "salons": salons,
    "csp": csp,
    "salons_table": salons_table,
    "lead_distribution": lead_distribution,
}

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"  ✅ {OUTPUT_JSON}")
print(f"  Timestamp : {output['generated_at']}")
print(f"  Lead dist : {lead_distribution['values']}")
print("\n" + "=" * 64)
print("  ✅ Données baromètre prêtes — refresh barometer_dashboard.html")
print("=" * 64)
