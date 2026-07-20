import re
import unicodedata

ZONE_CMS1_NAME = "ZONE CMS1 - COMPONENT SURFACE MOUNTING"
ZONE_CMS2_NAME = "ZONE CMS2 - TEST ZONE (Résumé des Machines Essentielles)"

ZONE_OPTIONS = [
    ZONE_CMS1_NAME,
    ZONE_CMS2_NAME,
]

SOUS_ZONE_OPTIONS_BY_ZONE = {
    ZONE_CMS1_NAME: [
        "CMS LINE 1 (e.g., BBS - Broadband Products)",
        "CMS LINE 2 (e.g., AVS - Audio Video Products)",
    ],
    ZONE_CMS2_NAME: [
        "TEST IN-SITU (Test des Composants)",
        "TEST FONCTIONNEL (Test de Fonctionnement)",
        "TEST WiFi (Test Sans Fil)",
    ],
}

ORDRE_TEMPLATES = {
    ZONE_CMS1_NAME: {
        "CMS LINE 1 (e.g., BBS - Broadband Products)": [
            {"ordre": 1, "nom": "Dépileur (Card Loader)"},
            {"ordre": 2, "nom": "Machine de Sérigraphie (DEK/MPM)"},
            {"ordre": 3, "nom": "Machine de Pose (Pick & Place)"},
            {"ordre": 4, "nom": "Machine SPI (Solder Paste Inspection)"},
            {"ordre": 5, "nom": "Machine 2D Scanner (Component Inspection)"},
            {"ordre": 6, "nom": "Machine AOI 3D (Final Inspection)"},
            {"ordre": 7, "nom": "Four de Refusions (Reflow Oven)"},
            {"ordre": 8, "nom": "Poste Insertion Manuelle (Manual THT)"},
            {"ordre": 9, "nom": "Machine de Brassage à la Vague (Wave Soldering)"},
        ],
        "CMS LINE 2 (e.g., AVS - Audio Video Products)": [
            {"ordre": 1, "nom": "Dépileur"},
            {"ordre": 2, "nom": "Machine de Sérigraphie"},
            {"ordre": 3, "nom": "Machine de Pose"},
            {"ordre": 4, "nom": "Machine SPI"},
            {"ordre": 5, "nom": "Machine 2D Scanner"},
            {"ordre": 6, "nom": "Machine AOI 3D"},
            {"ordre": 7, "nom": "Four de Refusions"},
            {"ordre": 8, "nom": "Poste Insertion Manuelle"},
            {"ordre": 9, "nom": "Machine de Brassage à la Vague"},
        ],
    },
    ZONE_CMS2_NAME: {
        "TEST IN-SITU (Test des Composants)": [
            {"ordre": 1, "nom": "Interface de Test (Bed of Nails)"},
            {"ordre": 2, "nom": "Testeur Marconi 4220"},
        ],
        "TEST FONCTIONNEL (Test de Fonctionnement)": [
            {"ordre": 1, "nom": "Banc TF"},
            {"ordre": 2, "nom": "BFE (Banc Front End)"},
            {"ordre": 3, "nom": "BAV (Banc Audio Video)"},
            {"ordre": 4, "nom": "Routeur"},
        ],
        "TEST WiFi (Test Sans Fil)": [
            {"ordre": 1, "nom": "PC avec Logiciels de Test"},
            {"ordre": 2, "nom": "Caisson Faraday (Shielding Box)"},
            {"ordre": 3, "nom": "IQflex Analyzer"},
            {"ordre": 4, "nom": "Routeur"},
            {"ordre": 5, "nom": "Switch"},
            {"ordre": 6, "nom": "Atténuateurs (30dB, 6dB, 3dB)"},
            {"ordre": 7, "nom": "Power Splitter"},
        ],
    },
}

MACHINE_STATUS_OPTIONS = [
    "OPERATIONNELLE",
    "EN_MAINTENANCE",
    "EN_PANNE",
    "HORS_SERVICE",
]


SUBZONE_SHORT = {
    "CMS LINE 1 (e.g., BBS - Broadband Products)": "L1",
    "CMS LINE 2 (e.g., AVS - Audio Video Products)": "L2",
    "TEST IN-SITU (Test des Composants)": "ISITU",
    "TEST FONCTIONNEL (Test de Fonctionnement)": "TF",
    "TEST WiFi (Test Sans Fil)": "WIFI",
}

FILLER_WORDS = {"MACHINE", "POSTE", "FOUR", "DE", "DU", "DES", "LA", "LE", "LES", "AVEC"}


def _short_machine_name(nom: str) -> str:
    without_parens = re.sub(r"\(.*?\)", "", nom).strip()
    words = without_parens.split()
    remaining = [w for w in words if w.upper() not in FILLER_WORDS]
    if not remaining:
        return without_parens
    if len(remaining[0]) <= 2 and len(remaining) > 1:
        return f"{remaining[0]} {remaining[1]}"
    return remaining[0]


def generate_machine_name(zone: str, sous_zone: str, ordre: str) -> str:
    """Generate the standardized machine name matching frontend logic."""
    if not zone or not sous_zone or not ordre:
        return ""

    cms_number = ""
    if "CMS1" in zone:
        cms_number = "1"
    elif "CMS2" in zone:
        cms_number = "2"

    def strip_accents(s):
        s = unicodedata.normalize("NFD", s)
        return "".join(c for c in s if not unicodedata.combining(c))

    # Standardize strings: replace non-ALPHANUM sequence with a SINGLE underscore and strip
    def clean_str(s):
        s = re.sub(r"[^A-Z0-9]+", "_", strip_accents(s).upper())
        return s.strip("_")

    subzone_key = SUBZONE_SHORT.get(sous_zone) or clean_str(sous_zone).split("_")[0]

    order_name = ""
    try:
        ordre_int = int(ordre)
        templates = ORDRE_TEMPLATES.get(zone, {}).get(sous_zone, [])
        selected_template = next(
            (t for t in templates if t["ordre"] == ordre_int), None
        )
        if selected_template:
            order_name = clean_str(_short_machine_name(selected_template["nom"]))
    except ValueError:
        pass

    return f"CMS{cms_number}-{subzone_key}-{order_name}"
