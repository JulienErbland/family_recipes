SEASON_LABEL_FR = {
    "winter": "Hiver",
    "spring": "Printemps",
    "summer": "Été",
    "fall": "Automne",
}

ROLE_LABEL_FR = {
    "reader": "Lecteur",
    "editor": "Éditeur",
}

def season_label_fr(key: str) -> str:
    return SEASON_LABEL_FR.get(key, key)

def seasons_label_fr(keys) -> str:
    keys = keys or []
    if set(keys) == {"winter", "spring", "summer", "fall"}:
        return "Toute l’année"
    return ", ".join(season_label_fr(k) for k in keys if k)

def role_label_fr(role: str) -> str:
    return ROLE_LABEL_FR.get(role or "", role or "")