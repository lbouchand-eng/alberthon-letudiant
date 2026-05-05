"""Seed app.db: demo users + articles. Idempotent — safe to re-run."""
from datetime import datetime, timedelta

import auth as auth_mod

DEMO_USERS = [
    dict(email="admin@letudiant.fr",   password="demo2026", school_name="L'Étudiant — Admin",
         role="admin",  plan="admin",         quota_leads=999999, status="active"),
    dict(email="client@iseg.fr",       password="demo2026", school_name="ISEG Paris",
         role="client", plan="premium_leads", quota_leads=2000,   status="active"),
    dict(email="bts@lyceefoch.fr",     password="demo2026", school_name="Lycée Foch — BTS",
         role="client", plan="starter",       quota_leads=0,      status="active"),
    dict(email="leads@em-lyon.fr",     password="demo2026", school_name="emlyon Business School",
         role="client", plan="leads_only",    quota_leads=1500,   status="active"),
    dict(email="growth@kedge.com",     password="demo2026", school_name="Kedge BS",
         role="client", plan="growth",        quota_leads=0,      status="active"),
    dict(email="new@univ-lille.fr",    password="demo2026", school_name="Université de Lille",
         role="client", plan="starter",       quota_leads=0,      status="pending"),
]


ARTICLES = [
    dict(slug="tendances-orientation-2026",
         title="Orientation 2026 : ce que disent vraiment les 4 millions d'étudiants L'Étudiant",
         excerpt="Notre baromètre révèle un retournement majeur des intentions vers le commerce et la santé, au détriment des filières littéraires.",
         category="Tendances",
         author="La rédaction L'Étudiant",
         body="""## Une rentrée 2026 sous le signe du pragmatisme

Les **719 775 lycéens** déclarant viser une filière commerce/vente sur la base L'Étudiant placent ce domaine en tête, devant la santé (479 952) et les arts (465 790). C'est la **première fois en cinq ans** que le commerce dépasse la santé sur la mesure d'intention déclarée — un signal fort pour les écoles de management qui doivent ajuster leur sourcing.

### 608 000 indécis — un gisement d'opportunité

Près de **15 % de la base** se déclare sans projet précis. Ces profils, longtemps considérés comme à faible valeur commerciale, deviennent en réalité les leads les plus intéressants une fois engagés via l'agent conversationnel d'orientation. Notre scoring intent-based les classe **B (tiède)** pour 60 % d'entre eux après 3 interactions.

### Méthodologie

Données extraites de BigQuery `letudiant-data-prod.Hacka_g23` au 28 avril 2026, pondérées par les probabilités CSP INSEE et filtrées sur les contacts ayant un consentement commercial actif.
"""),
    dict(slug="cpl-vs-cpc-ecoles",
         title="CPL vs CPC : pourquoi les écoles passent au coût par lead qualifié",
         excerpt="Avec un taux de conversion de 6 à 9 % contre 2 à 3 % pour les leads génériques, le CPL intent-based bouleverse les budgets d'acquisition.",
         category="Marketing",
         author="Léa Dupré",
         body="""Une école qui paie **32 €** un lead A (chaud) chez L'Étudiant le convertit en moyenne **3× plus souvent** qu'un lead générique acheté 8 € via display programmatique. Le calcul est imparable :

- **Coût d'acquisition** d'un inscrit : 350-450 € sur leads génériques, 180-280 € sur leads A.
- **Valeur d'un inscrit** : 5 000 à 25 000 € sur la durée du cursus.
- **ROI à 12 mois** : ×4 à ×7 vs ×2 sur les canaux traditionnels.

La condition : avoir une équipe commerciale capable de traiter le lead **dans les 48 h**. Au-delà, l'avantage CPL s'érode rapidement.
"""),
    dict(slug="rgpd-orientation-leads",
         title="RGPD et leads étudiants : ce que les écoles peuvent et ne peuvent pas faire",
         excerpt="Consentement, mineurs, durée de conservation : tour d'horizon des obligations à 6 mois de la prochaine vague d'inspections CNIL.",
         category="Conformité",
         author="Maître Adam Mercier",
         body="""## Trois règles incontournables

1. **Consentement explicite** (`optin_commercial_actuel = TRUE`) : sans cela, aucune transmission. La base légale d'« intérêt légitime » couvre le scoring interne, pas la prospection.
2. **Mineurs** : interdiction de prospection commerciale en dessous de 15 ans sans accord parental. Filtrer systématiquement les classes 3ᵉ et 4ᵉ.
3. **Durée de conservation** : 3 ans après dernier contact actif, puis purge ou archivage à accès restreint.

L'AIPD (analyse d'impact RGPD) reste **obligatoire** avant toute mise en production industrielle d'un dispositif de scoring d'intention.
"""),
    dict(slug="salons-orientation-roi",
         title="Les salons d'orientation valent-ils encore le coup ?",
         excerpt="Avec 72 % de présence effective et une corrélation forte avec la conversion finale, les salons restent le canal le plus rentable — à condition d'y être.",
         category="Recrutement",
         author="La rédaction L'Étudiant",
         body="""**3 513 287 inscriptions, 72 % de présence**. Les salons L'Étudiant restent le rendez-vous incontournable. Notre data montre que les inscrits venus à un salon ont **2,3× plus de chances** de finaliser une inscription dans les 90 jours.

Top 3 villes par taux de présence : Clermont-Ferrand (80 %), Montpellier (79 %), Caen (78 %). Paris reste le plus gros bassin en volume mais avec un taux plus modeste (56 %).
"""),
    dict(slug="chatbot-orientation-impact",
         title="L'agent conversationnel d'orientation : 56 605 conversations, qu'apprend-on ?",
         excerpt="Le pic de janvier (12 710 conversations) coïncide avec la phase Parcoursup. Données et insights de notre IA d'orientation.",
         category="Produit",
         author="Sarah Cohen",
         body="""L'usage de l'agent conversationnel double pendant la période Parcoursup (15 jan. - 15 mars). Les Terminales représentent **68 % des conversations** mais seulement 22 % de la base — un signe clair que le besoin d'orientation se concentre sur cette tranche.

Les questions les plus fréquentes : « Quelle école pour [X] ? » (34 %), « Combien ça coûte ? » (28 %), « Et après le diplôme ? » (19 %).
"""),
    dict(slug="csp-filieres-orientation",
         title="Filières d'orientation et CSP : ce que la donnée INSEE révèle",
         excerpt="Le commerce et le digital attirent davantage les profils CSP+, tandis que la santé et l'enseignement restent plus mixtes.",
         category="Sociologie",
         author="Pr. Karim Benali",
         body="""En croisant les **probabilités CSP INSEE** avec les déclarations d'intention sur la base L'Étudiant, des patterns nets émergent. Le commerce concentre **20 % de profils CSP+** contre 12 % en moyenne nationale. La santé reste le domaine le plus mixte socialement.

Pour les écoles de commerce, ce signal a un impact direct sur la grille tarifaire et les politiques de bourses.
"""),
    dict(slug="hackathon-alberthon-2026",
         title="Inside : comment Alberthon a construit ce produit en 48 h",
         excerpt="Retour sur la session On the Grill #2 : du brief à un pipeline BigQuery + dashboard live + business plan complet.",
         category="Coulisses",
         author="L'équipe Alberthon",
         body="""**Vendredi 18 h** : brief de L'Étudiant. **Dimanche 18 h** : pipeline complet, dashboard interactif, modèle financier 3 ans, fiches produit. Le secret : combiner les sujets 1 (Baromètre) et 3 (Marketing automation) plutôt que les traiter en silos.

Le pipeline `pipeline_lead_scoring.py` synthétise 4 millions d'inscrits + 250 millions d'événements CRM en moins de 5 minutes sur BigQuery, et produit une table actionnable de leads scorés A/B/C.
"""),
    dict(slug="business-plan-saas-edu",
         title="Business plan d'un SaaS data pour l'éducation : 3 chiffres clés",
         excerpt="Marge brute ≥ 90 % en année 2, churn maîtrisé sous 12 %, conversion à 8 % : les benchmarks d'un SaaS data B2B éducation.",
         category="Stratégie",
         author="Léonard Bouchand",
         body="""Sur les 3 années projetées : **525 k€** de revenu en année 1, **1,8 M€** en année 2, **5 M€** en année 3. La marge brute monte de 80 % à 96 % — typique d'un SaaS qui industrialise son ingestion.

Le risque principal : la **dépendance à l'opt-in commercial**. Si le taux d'opt-in passe de 36 % à 25 %, le revenu CPL chute de 30 %. D'où l'importance de pages de consentement claires et engageantes.
"""),
]


def seed_users():
    print("→ Création des comptes démo…")
    for u in DEMO_USERS:
        if auth_mod.User.by_email(u["email"]):
            print(f"  · existe déjà : {u['email']}")
            continue
        auth_mod.User.create(**u)
        print(f"  ✓ {u['email']:30s}  ({u['plan']})")


def seed_articles():
    print("→ Création des articles éditoriaux…")
    conn = auth_mod.get_db()
    base = datetime.utcnow()
    for i, art in enumerate(ARTICLES):
        existing = conn.execute(
            "SELECT id FROM articles WHERE slug = ?", (art["slug"],)
        ).fetchone()
        if existing:
            print(f"  · existe déjà : {art['slug']}")
            continue
        published = (base - timedelta(days=i * 4)).isoformat(timespec="seconds")
        conn.execute(
            """INSERT INTO articles (slug, title, excerpt, body, author, category, published_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (art["slug"], art["title"], art["excerpt"], art["body"],
             art["author"], art["category"], published),
        )
        print(f"  ✓ {art['slug']}")
    conn.commit()
    conn.close()


def main():
    print("=" * 60)
    print("  SEED — L'Étudiant × Alberthon webapp")
    print("=" * 60)
    auth_mod.init_db()
    seed_users()
    seed_articles()
    print("\n✅ Seed terminé. Lancez maintenant :  python app.py")
    print("\nComptes démo :")
    for u in DEMO_USERS:
        print(f"  · {u['email']:30s}  /  {u['password']}   [{u['plan']}, {u['status']}]")


if __name__ == "__main__":
    main()
