"""
Pipeline Lead Scoring — L'Étudiant x Alberthon
=================================================
Produit : Intent-Based Lead Scoring pour écoles partenaires
Direction : Fusion Sujet 1 (Baromètre orientation) + Sujet 3 (Marketing automation)

Ce pipeline :
  1. Lit les tables sources depuis BigQuery
  2. Calcule un score d'intention sur 3 dimensions
  3. Classe chaque inscrit en lead A / B / C
  4. Écrit la table de sortie dans BigQuery (ou CSV local)

Exécution :
  pip install google-cloud-bigquery pandas
  python pipeline_lead_scoring.py
"""

import os
from pathlib import Path
from datetime import datetime
import sys

# ── Configuration ────────────────────────────────────────────────────────────
PROJECT   = "letudiant-data-prod"
DATASET   = "Hacka_g23"
CREDS     = str(Path(__file__).parent.parent.parent / "application_default_credentials.json")
OUTPUT_TABLE = f"{PROJECT}.{DATASET}.lead_scores_output"   # table BigQuery de sortie
OUTPUT_CSV   = str(Path(__file__).parent / "lead_scores_output.csv")  # sortie locale

# Mode test : limiter les données pour déboguer
TEST_MODE = "--test" in sys.argv  # Utilise --test pour exécuter en mode test

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDS

from google.cloud import bigquery
import pandas as pd

# Créer le client
client = bigquery.Client(project=PROJECT)

print("=" * 60)
print("  Pipeline Lead Scoring — L'Étudiant")
print(f"  Exécuté le {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 60)


# ── Étape 1 : Extraction ─────────────────────────────────────────────────────
print("\n[1/4] Extraction des données depuis BigQuery...")
print("  (Ce peut prendre quelques minutes la première fois...)")

LIMIT_CLAUSE = "\nLIMIT 1000" if TEST_MODE else ""

QUERY = f"""
SELECT
  si.id_Inscrit_site,
  sl.study_level,
  de.domaine_etude,
  p.profile,
  si.Acquisition_source,
  si.Departement,
  si.Region,
  si.Academie,
  si.Date_de_creation,
  si.Revenu_Median_Menage,
  si.Proba_CSP_Plus,
  si.Proba_CSP_Moins,
  si.ACTIF,
  si.optin_letudiant_actuel,
  si.optin_commercial_actuel,

  -- Signaux salon (présence physique = forte intention)
  MAX(CASE WHEN sal.id_Inscrit_site IS NOT NULL THEN 1 ELSE 0 END) AS a_visite_salon,
  MAX(CASE WHEN sal.Showed_up = TRUE THEN 1 ELSE 0 END)            AS est_venu_salon,
  COUNT(DISTINCT sal.Event_id)                                      AS nb_salons,
  STRING_AGG(DISTINCT sal.study_field_interests, ' | ' LIMIT 3)    AS interets_salon,

  -- Signaux CRM (engagement email)
  COUNTIF(crm.opened  = TRUE) AS nb_emails_ouverts,
  COUNTIF(crm.clicked = TRUE) AS nb_emails_cliques,
  COUNT(DISTINCT crm.ID_Camp) AS nb_campagnes_recues,

  -- Signaux agent conversationnel (intention déclarée)
  MAX(CASE WHEN conv.id_Inscrit_site IS NOT NULL THEN 1 ELSE 0 END) AS a_utilise_agent,
  COUNT(DISTINCT conv.id)                                            AS nb_conversations,
  MAX(conv.feedback)                                                 AS feedback_agent

FROM `{PROJECT}.{DATASET}.Site_Inscrits` si
LEFT JOIN `{PROJECT}.{DATASET}.Site_Inscrits_dimension_study_level`  sl  ON si.id_study_level    = sl.id_study_level
LEFT JOIN `{PROJECT}.{DATASET}.Site_Inscrits_dimension_domaine_etude` de ON si.id_domaine_etude   = de.id_domaine_etude
LEFT JOIN `{PROJECT}.{DATASET}.Site_Inscrits_dimension_profile`       p   ON si.id_profile         = p.id_profile
LEFT JOIN `{PROJECT}.{DATASET}.Salons_Inscrits_et_venus`              sal ON si.id_Inscrit_site    = sal.id_Inscrit_site
LEFT JOIN `{PROJECT}.{DATASET}.CRM_Communication`                     crm ON si.id_Inscrit_site    = crm.id_Inscrit_site
LEFT JOIN `{PROJECT}.{DATASET}.Agent_Conversationnel_ORI_Conversation` conv ON si.id_Inscrit_site = conv.id_Inscrit_site

GROUP BY
  si.id_Inscrit_site, sl.study_level, de.domaine_etude, p.profile,
  si.Acquisition_source, si.Departement, si.Region, si.Academie,
  si.Date_de_creation, si.Revenu_Median_Menage,
  si.Proba_CSP_Plus, si.Proba_CSP_Moins, si.ACTIF,
  si.optin_letudiant_actuel, si.optin_commercial_actuel
{LIMIT_CLAUSE}
"""

try:
    print("  ⏳ Exécution de la requête...")
    query_job = client.query(QUERY)
    print(f"  ⏳ Téléchargement des résultats...")
    df = query_job.to_dataframe(create_bqstorage_client=False, timeout=600)  # 10 minutes timeout
    print(f"  ✅ {len(df):,} inscrits extraits")
    if TEST_MODE:
        print(f"  📝 [MODE TEST] Limité à 1000 inscrits")
except Exception as e:
    import traceback
    print(f"  ❌ Erreur lors de l'extraction : {e}")
    traceback.print_exc()
    sys.exit(1)


# ── Étape 2 : Scoring sur 3 dimensions ───────────────────────────────────────
print("\n[2/4] Calcul du score d'intention (3 dimensions × 100 pts)...")

# Dimension A — Fraîcheur (30 pts)
# Inscrit récemment + actif = signal frais
def score_fraicheur(row):
    score = 0
    if row["ACTIF"] in ("Actif", "Toujours inscrit"):
        score += 15
    try:
        created = pd.to_datetime(row["Date_de_creation"])
        days_old = (datetime.now() - created.replace(tzinfo=None)).days
        if days_old < 180:   score += 15
        elif days_old < 365: score += 10
        elif days_old < 730: score += 5
    except Exception:
        pass
    return min(score, 30)

# Dimension B — Clarté de l'intention (40 pts)
# Filière définie + niveau défini + agent utilisé + salon
DOMAINES_FLOUS = {"Je ne sais pas quoi faire", "(Vide)", None, ""}
def score_intention(row):
    score = 0
    if row.get("domaine_etude") not in DOMAINES_FLOUS:
        score += 15
    if row.get("study_level") and row["study_level"] not in ("(Vide)", ""):
        score += 10
    if row.get("a_utilise_agent", 0) == 1:
        score += 10
    if row.get("est_venu_salon", 0) == 1:
        score += 5
    return min(score, 40)

# Dimension C — Engagement & données (30 pts)
def score_engagement(row):
    score = 0
    opens   = int(row.get("nb_emails_ouverts", 0) or 0)
    clicks  = int(row.get("nb_emails_cliques", 0) or 0)
    salons  = int(row.get("nb_salons", 0) or 0)
    if opens  > 5:  score += 10
    elif opens > 0: score += 5
    if clicks > 2:  score += 10
    elif clicks > 0: score += 5
    if salons >= 2: score += 10
    elif salons == 1: score += 5
    return min(score, 30)

df["score_fraicheur"]  = df.apply(score_fraicheur,  axis=1)
df["score_intention"]  = df.apply(score_intention,  axis=1)
df["score_engagement"] = df.apply(score_engagement, axis=1)
df["score_total"]      = df["score_fraicheur"] + df["score_intention"] + df["score_engagement"]


# ── Étape 3 : Classification A / B / C ───────────────────────────────────────
print("\n[3/4] Classification des leads...")

def classify(score):
    if score >= 55: return "A"   # Lead chaud — fort potentiel de conversion
    if score >= 30: return "B"   # Lead tiède — à nurturer
    return "C"                   # Lead froid — base à activer

df["lead_class"] = df["score_total"].apply(classify)

dist = df["lead_class"].value_counts()
print(f"  A (chauds)  : {dist.get('A', 0):>8,} leads")
print(f"  B (tièdes)  : {dist.get('B', 0):>8,} leads")
print(f"  C (froids)  : {dist.get('C', 0):>8,} leads")
print(f"  TOTAL       : {len(df):>8,} leads")


# ── Étape 4 : Export ──────────────────────────────────────────────────────────
print("\n[4/4] Export des résultats...")

OUTPUT_COLS = [
    "id_Inscrit_site", "study_level", "domaine_etude", "profile",
    "Region", "Departement", "Academie",
    "score_fraicheur", "score_intention", "score_engagement", "score_total",
    "lead_class",
    "a_visite_salon", "est_venu_salon", "nb_salons", "interets_salon",
    "nb_emails_ouverts", "nb_emails_cliques", "nb_campagnes_recues",
    "a_utilise_agent", "nb_conversations",
    "optin_letudiant_actuel", "optin_commercial_actuel",
    "Proba_CSP_Plus", "Proba_CSP_Moins", "Revenu_Median_Menage",
    "ACTIF"
]

df_out = df[[c for c in OUTPUT_COLS if c in df.columns]]

# Export CSV local
df_out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
print(f"  ✅ CSV local sauvegardé : {OUTPUT_CSV}")

# Export BigQuery (optionnel — décommenter pour écrire dans BQ)
# job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
# client.load_table_from_dataframe(df_out, OUTPUT_TABLE, job_config=job_config).result()
# print(f"  ✅ Table BigQuery mise à jour : {OUTPUT_TABLE}")

print("\n" + "=" * 60)
print("  Pipeline terminé avec succès ✅")
print(f"  Score moyen : {df['score_total'].mean():.1f} / 100")
print(f"  Table de sortie : {OUTPUT_CSV}")
print("=" * 60 + "\n")
