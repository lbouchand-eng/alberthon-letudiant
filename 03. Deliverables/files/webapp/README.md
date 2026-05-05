# L'Étudiant Data — Webapp (site vitrine + portail entreprises)

Application Flask qui transforme les livrables hackathon (`pipeline_lead_scoring.py`,
`barometer_dashboard.html`, fiches produit, business plan) en un parcours commercial
unifié : site marketing + portail authentifié pour les écoles partenaires.

## Lancer en local

```bash
cd "03. Deliverables/files/webapp"
python3 -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -r requirements.txt
python seed.py                    # crée app.db + comptes démo + 8 articles
python app.py                     # http://localhost:5050
```

## Comptes de démo

| Email                   | Mot de passe | Plan             | Statut  |
|-------------------------|--------------|------------------|---------|
| admin@letudiant.fr      | demo2026     | admin            | actif   |
| client@iseg.fr          | demo2026     | premium + leads  | actif   |
| bts@lyceefoch.fr        | demo2026     | starter          | actif   |
| leads@em-lyon.fr        | demo2026     | leads_only       | actif   |
| growth@kedge.com        | demo2026     | growth           | actif   |
| new@univ-lille.fr       | demo2026     | starter          | pending |

## Arborescence

```
webapp/
├── app.py                  # Flask app (routes publiques + auth + portail)
├── auth.py                 # Modèle User, SQLite, bcrypt, logs RGPD
├── leads_service.py        # Lecture lead_scores_output.csv + filtres + export
├── barometer_service.py    # Lecture barometer_data.json
├── pipeline_adapter.py     # Hook vers pipeline_lead_scoring.py (BigQuery)
├── seed.py                 # Comptes démo + articles éditoriaux
├── app.db                  # SQLite (généré)
├── requirements.txt
├── static/
│   ├── css/{style,dashboard}.css
│   ├── js/{charts,leads-table}.js
│   └── img/logo.svg
└── templates/
    ├── base.html
    ├── public/             # home, produits, tarifs, articles, à-propos, contact, 404
    ├── auth/               # login, signup
    └── portal/             # dashboard, baromètre, leads, billing, compliance, profile
```

## Plans et capacités

| Plan             | Baromètre | Leads CPL | Quota leads/an |
|------------------|-----------|-----------|----------------|
| starter          | ✓         | —         | 0              |
| growth           | ✓         | —         | 0              |
| premium          | ✓         | ✓         | 500            |
| leads_only       | —         | ✓         | 1 500          |
| premium_leads    | ✓         | ✓         | 2 000          |
| admin            | ✓         | ✓         | illimité       |

## RGPD by design

L'export CSV des leads garantit :
- Filtre `optin_commercial_actuel = TRUE` appliqué côté serveur
- Aucune colonne nominative (email, téléphone) dans l'export
- Plafonnement automatique au quota restant
- Log d'accès enregistré dans `access_log` (consultable via `/portal/compliance`)

## Hors scope v1

- Paiement Stripe (jauge simulée seulement)
- Validation email lors du signup (manuelle par admin)
- BigQuery temps réel — voir `pipeline_adapter.py` pour le hook
- API REST publique
- Multi-tenant SSO

## Pages clés

- `/` — site vitrine (hero + 4 KPI + 2 cartes produits + témoignages)
- `/tarifs` — 3 plans Baromètre + 3 tiers leads CPL
- `/articles` — 8 articles éditoriaux préchargés
- `/portal/leads` — tableau filtrable + export CSV (RGPD)
- `/portal/barometre` — 6 graphes Chart.js du baromètre
- `/portal/billing` — quota, simulation de coût, historique
- `/portal/compliance` — DPA, AIPD, journal d'accès
