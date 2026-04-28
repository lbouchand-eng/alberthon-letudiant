# Pipeline Lead Scoring & Baromètre des Intentions d'Orientation
**L'Étudiant × Alberthon — Hackathon 2026**

> Direction produit : Fusion Sujet 1 (Baromètre orientation) + Sujet 3 (Marketing automation)  
> Session On the Grill #2 — 29 avril 2026

---

## Vue d'ensemble

Ce dépôt contient le pipeline de données et les livrables associés pour deux produits data développés sur la base BigQuery de L'Étudiant (`letudiant-data-prod.Hacka_g23`) :

| Produit | Type | Description |
|---------|------|-------------|
| **Baromètre des Intentions d'Orientation** | SaaS annuel | Dashboard de tendances d'orientation en temps réel pour les établissements |
| **Leads Qualifiés Intent-Based** | CPL | Flux de leads étudiants scorés A/B/C livré aux écoles partenaires |

---

## Structure du projet

```
03. OnTheGrill Session #2/
├── pipeline_lead_scoring.py      # Pipeline principal (extraction + scoring + export)
├── barometer_dashboard.html      # Dashboard Baromètre interactif (5 insights live)
├── lead_scores_output.csv        # Table de sortie : leads scorés A/B/C
├── fiches_produit.docx           # 2 product specs au standard brief
├── business_plan.xlsx            # Modèle financier 3 ans + sensibilité
├── note_conformite_RGPD.docx     # Note de conformité RGPD
└── README.md                     # Ce fichier
```

---

## Pipeline : `pipeline_lead_scoring.py`

### Prérequis

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install google-cloud-bigquery pandas
```

### Configuration

Placer le fichier `application_default_credentials.json` à la **racine du projet** (un niveau au-dessus de ce dossier). Obtenu via :

```bash
gcloud auth application-default login
```

### Exécution

```bash
python pipeline_lead_scoring.py
```

Ou via le lanceur depuis la racine du projet :
```bash
run_pipeline.bat               # Windows
```

### Sources de données (BigQuery)

| Table | Lignes | Rôle dans le pipeline |
|-------|--------|-----------------------|
| `Site_Inscrits` | 4 058 555 | Base principale — profil, géo, CSP, optins |
| `Agent_Conversationnel_ORI_Conversation` | 56 605 | Signal d'intention déclarée (agent IA) |
| `CRM_Communication` | 249 295 516 | Signal d'engagement comportemental (email) |
| `Salons_Inscrits_et_venus` | 3 513 287 | Signal d'intention physique (présence salon) |
| `Site_Inscrits_dimension_*` | — | Tables de dimension (filière, niveau, profil, série) |

### Logique de scoring (3 dimensions, 100 points)

#### Dimension 1 — Fraîcheur (30 pts)
Mesure la récence et l'activité du contact.

| Critère | Points |
|---------|--------|
| Statut ACTIF / Toujours inscrit | +15 |
| Inscription < 6 mois | +15 |
| Inscription 6-12 mois | +10 |
| Inscription 12-24 mois | +5 |

#### Dimension 2 — Clarté de l'intention (40 pts)
Mesure la précision du projet d'orientation déclaré.

| Critère | Points |
|---------|--------|
| Domaine d'étude déclaré et précis (non "Je ne sais pas") | +15 |
| Niveau scolaire renseigné | +10 |
| A utilisé l'agent conversationnel d'orientation | +10 |
| Est venu physiquement à un salon | +5 |

#### Dimension 3 — Engagement (30 pts)
Mesure l'intensité des interactions comportementales.

| Critère | Points |
|---------|--------|
| > 5 emails ouverts | +10 |
| 1-5 emails ouverts | +5 |
| > 2 emails cliqués | +10 |
| 1-2 emails cliqués | +5 |
| ≥ 2 salons fréquentés | +10 |
| 1 salon fréquenté | +5 |

### Classification des leads

| Classe | Score | Profil | Prix indicatif |
|--------|-------|--------|----------------|
| **A** | ≥ 55 | Lead chaud — intention forte + engagement élevé | 25-40 €/lead |
| **B** | 30-54 | Lead tiède — à nurturer | 8-15 €/lead |
| **C** | < 30 | Lead froid — campagnes notoriété | 2-4 €/lead |

### Table de sortie : `lead_scores_output`

Colonnes exportées :

```
id_Inscrit_site | study_level | domaine_etude | profile | Region | Departement
score_fraicheur | score_intention | score_engagement | score_total | lead_class
a_visite_salon | est_venu_salon | nb_salons | nb_emails_ouverts | nb_emails_cliques
a_utilise_agent | nb_conversations | optin_letudiant_actuel | optin_commercial_actuel
Proba_CSP_Plus | Proba_CSP_Moins | ACTIF
```

> ⚠️ Seuls les contacts avec `optin_commercial_actuel = TRUE` sont transmis aux établissements partenaires.

---

## Dashboard Baromètre : `barometer_dashboard.html`

Ouvrir directement dans un navigateur. Aucune dépendance serveur requise.

**5 insights disponibles :**
1. Top filières par volume d'intention (4M inscrits)
2. Activité de l'agent conversationnel IA par mois
3. Taux d'engagement email par niveau scolaire
4. Présence aux salons par ville (saison 25/26)
5. Répartition CSP par filière d'intention

**Filtres interactifs :** niveau scolaire · profil CSP · ville salon

---

## Conformité RGPD

Voir `note_conformite_RGPD.docx` pour le détail complet.

Points clés :
- **Base légale principale** : intérêt légitime (art. 6.1.f) pour le scoring interne
- **Transmission aux établissements** : uniquement sur consentement explicite (`optin_commercial_actuel`)
- **Données pseudonymisées** : email et téléphone stockés en BYTES, jamais transmis en clair
- **Mineurs** : filtrage recommandé sur âge ≥ 15 ans avant scoring (3èmes/4èmes)
- **AIPD** : à conduire avant mise en production industrielle (art. 35 RGPD)

---

## Auteurs

Équipe Alberthon — Hackathon L'Étudiant 2026  
Contact : lbouchand@albertschool.com
