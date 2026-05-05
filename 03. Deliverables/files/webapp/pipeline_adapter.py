"""Optional bridge to pipeline_lead_scoring.py (admin-only refresh).

For the demo we *do not* re-run BigQuery on each request: the CSV produced by
the existing pipeline (lead_scores_output.csv) is read once at boot. This
module exists to document how to plug the live BigQuery pipeline back in if
Google Cloud credentials become available.
"""
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
CREDS_PATH = ROOT.parent.parent / "application_default_credentials.json"


def credentials_available() -> bool:
    return CREDS_PATH.exists()


def refresh_from_bigquery():
    """Re-run pipeline_lead_scoring.py — refreshes lead_scores_output.csv.

    Not wired to a route by default. Returns (ok: bool, message: str).
    """
    if not credentials_available():
        return False, (
            "Credentials BigQuery non détectés. Placez "
            f"{CREDS_PATH.name} à la racine du projet pour activer le refresh."
        )
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(CREDS_PATH)
    try:
        # importing the module triggers the full pipeline
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "pipeline_lead_scoring", ROOT / "pipeline_lead_scoring.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return True, "Pipeline relancé. lead_scores_output.csv mis à jour."
    except Exception as e:
        return False, f"Erreur lors du refresh : {e}"
