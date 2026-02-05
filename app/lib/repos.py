from typing import Optional, List, Dict
from app.lib.supabase_client import get_supabase, authed_postgrest


def get_my_role(access_token: str) -> str:
    sb = authed_postgrest(get_supabase(), access_token)

    res = (
        sb.table("profiles")
        .select("role")
        .maybe_single()   # <-- CRITICAL CHANGE
        .execute()
    )

    if res.data and res.data.get("role"):
        return res.data["role"]

    # If profile row does not exist yet
    return "reader"

def ensure_my_profile(access_token: str, user_id: str) -> None:
    sb = authed_postgrest(get_supabase(), access_token)

    existing = (
        sb.table("profiles")
        .select("id")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )

    if existing.data:
        return

    sb.table("profiles").insert({"id": user_id, "role": "reader"}).execute()



def list_ingredients(access_token: str) -> List[Dict]:
    sb = authed_postgrest(get_supabase(), access_token)
    res = sb.table("ingredients").select("id,name").order("name").execute()
    return res.data or []

def create_ingredient(access_token: str, name: str) -> Dict:
    sb = authed_postgrest(get_supabase(), access_token)
    res = sb.table("ingredients").insert({"name": name}).execute()
    return res.data[0] if res.data else {}

def find_ingredient_by_name(access_token: str, name: str) -> Optional[Dict]:
    sb = authed_postgrest(get_supabase(), access_token)
    res = sb.table("ingredients").select("id,name").eq("name", name).maybe_single().execute()
    return res.data

def create_recipe(access_token: str, payload: Dict) -> Dict:
    sb = authed_postgrest(get_supabase(), access_token)
    res = sb.table("recipes").insert(payload).execute()
    return res.data[0] if res.data else {}

def add_recipe_ingredient(access_token: str, payload: Dict) -> Dict:
    sb = authed_postgrest(get_supabase(), access_token)
    res = sb.table("recipe_ingredients").insert(payload).execute()
    return res.data[0] if res.data else {}

def list_recipes(access_token: str) -> List[Dict]:
    sb = authed_postgrest(get_supabase(), access_token)
    res = (
        sb.table("recipes")
        .select(
            "id,name,season,servings,prep_minutes,cook_minutes,total_minutes,created_by,"
            "instructions,notes"
        )
        .order("name", desc=False)
        .execute()
    )
    return res.data or []

def map_creator_ids_to_names(access_token: str, creator_ids: List[str]) -> Dict[str, str]:
    profiles = list_profiles_by_ids(access_token, creator_ids)
    id_to_name = {}
    for p in profiles:
        fn = (p.get("first_name") or "").strip()
        ln = (p.get("last_name") or "").strip()
        full = (fn + " " + ln).strip()
        id_to_name[p["id"]] = full if full else p["id"]
    return id_to_name


def get_recipe_ingredients(access_token: str, recipe_id: str) -> List[Dict]:
    sb = authed_postgrest(get_supabase(), access_token)
    # This returns recipe_ingredients rows with a nested ingredient name
    res = (
        sb.table("recipe_ingredients")
        .select("ingredient_id,quantity,unit,comment,ingredients(name)")
        .eq("recipe_id", recipe_id)
        .execute()
    )
    return res.data or []

def list_recipe_ingredients(access_token: str) -> List[Dict]:
    sb = authed_postgrest(get_supabase(), access_token)
    res = (
        sb.table("recipe_ingredients")
        .select("recipe_id,quantity,unit,comment,ingredients(name)")
        .execute()
    )
    return res.data or []


def list_profiles_by_ids(access_token: str, user_ids: List[str]) -> List[Dict]:
    """
    Fetch profiles for a set of user ids (UUIDs).
    Returns rows like: {id, first_name, last_name, role}
    """
    if not user_ids:
        return []

    sb = authed_postgrest(get_supabase(), access_token)

    # Supabase python client supports "in_" in most versions:
    res = (
        sb.table("profiles")
        .select("id,first_name,last_name,role")
        .in_("id", user_ids)
        .execute()
    )
    return res.data or []

def list_my_recipes(access_token: str, user_id: str) -> List[Dict]:
    sb = authed_postgrest(get_supabase(), access_token)
    res = (
        sb.table("recipes")
        .select(
            "id,name,season,servings,prep_minutes,cook_minutes,total_minutes,created_by,"
            "instructions,notes,created_at,updated_at"
        )
        .eq("created_by", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []

def update_recipe(access_token: str, recipe_id: str, patch: Dict) -> Dict:
    sb = authed_postgrest(get_supabase(), access_token)
    allowed = {k: v for k, v in patch.items() if k in {
        "name", "season", "servings", "prep_minutes", "cook_minutes", "instructions", "notes"
    }}
    res = sb.table("recipes").update(allowed).eq("id", recipe_id).execute()
    return res.data[0] if res.data else {}

def delete_recipe(access_token: str, recipe_id: str) -> bool:
    sb = authed_postgrest(get_supabase(), access_token)
    res = sb.table("recipes").delete().eq("id", recipe_id).execute()
    return True

def delete_recipe_ingredient_link(access_token: str, recipe_id: str, ingredient_id: str) -> bool:
    sb = authed_postgrest(get_supabase(), access_token)
    sb.table("recipe_ingredients").delete().eq("recipe_id", recipe_id).eq("ingredient_id", ingredient_id).execute()
    return True

def update_recipe_ingredient_link(access_token: str, recipe_id: str, ingredient_id: str, patch: Dict) -> bool:
    sb = authed_postgrest(get_supabase(), access_token)
    allowed = {k: v for k, v in patch.items() if k in {"quantity", "unit", "comment"}}
    sb.table("recipe_ingredients").update(allowed).eq("recipe_id", recipe_id).eq("ingredient_id", ingredient_id).execute()
    return True

def set_my_role(access_token: str, user_id: str, role: str) -> bool:
    sb = authed_postgrest(get_supabase(), access_token)
    res = (
        sb.table("profiles")
        .update({"role": role})
        .eq("id", user_id)
        .execute()
    )
    return True
