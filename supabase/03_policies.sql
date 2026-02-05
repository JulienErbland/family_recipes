-- =========================================================
-- PROFILES (RLS)
-- =========================================================

-- Make sure RLS is enabled
alter table public.profiles enable row level security;

-- Remove old/conflicting policies
drop policy if exists "profiles: read own" on public.profiles;
drop policy if exists "profiles: read all (basic)" on public.profiles;
drop policy if exists "profiles: update own" on public.profiles;

-- READ: any logged-in user can read profiles (for showing creator names)
create policy "profiles: read all (basic)"
on public.profiles
for select
to authenticated
using (true);

-- UPDATE: user can update only their own profile
create policy "profiles: update own"
on public.profiles
for update
to authenticated
using (id = auth.uid())
with check (id = auth.uid());

-- PROFILES: allow a logged-in user to create THEIR OWN profile row
drop policy if exists "profiles: insert own" on public.profiles;

create policy "profiles: insert own"
on public.profiles
for insert
to authenticated
with check (
  id = auth.uid()
  and role = 'reader'
);



-- =========================================================
-- RECIPES
-- =========================================================

-- Any logged-in user can read all recipes
drop policy if exists "recipes: read all" on public.recipes;
create policy "recipes: read all"
on public.recipes
for select
to authenticated
using (true);

-- Editors can insert recipes, must set created_by = themselves
drop policy if exists "recipes: insert (editor)" on public.recipes;
create policy "recipes: insert (editor)"
on public.recipes
for insert
to authenticated
with check (
  exists (
    select 1 from public.profiles p
    where p.id = auth.uid() and p.role = 'editor'
  )
  and created_by = auth.uid()
);

-- Editors can update ONLY their own recipes
drop policy if exists "recipes: update own (editor)" on public.recipes;
create policy "recipes: update own (editor)"
on public.recipes
for update
to authenticated
using (
  created_by = auth.uid()
  and exists (
    select 1 from public.profiles p
    where p.id = auth.uid() and p.role = 'editor'
  )
)
with check (
  created_by = auth.uid()
  and exists (
    select 1 from public.profiles p
    where p.id = auth.uid() and p.role = 'editor'
  )
);

-- Editors can delete ONLY their own recipes
drop policy if exists "recipes: delete own (editor)" on public.recipes;
create policy "recipes: delete own (editor)"
on public.recipes
for delete
to authenticated
using (
  created_by = auth.uid()
  and exists (
    select 1 from public.profiles p
    where p.id = auth.uid() and p.role = 'editor'
  )
);

-- =========================================================
-- INGREDIENTS
-- =========================================================

-- Any logged-in user can read ingredients
drop policy if exists "ingredients: read all" on public.ingredients;
create policy "ingredients: read all"
on public.ingredients
for select
to authenticated
using (true);

-- Editors can add new ingredients
drop policy if exists "ingredients: insert (editor)" on public.ingredients;
create policy "ingredients: insert (editor)"
on public.ingredients
for insert
to authenticated
with check (
  exists (
    select 1 from public.profiles p
    where p.id = auth.uid() and p.role = 'editor'
  )
);

-- =========================================================
-- RECIPE_INGREDIENTS
-- =========================================================

-- Any logged-in user can read recipe_ingredients (needed to show recipe details)
drop policy if exists "recipe_ingredients: read all" on public.recipe_ingredients;
create policy "recipe_ingredients: read all"
on public.recipe_ingredients
for select
to authenticated
using (true);

-- Editors can link ingredients ONLY to recipes they own
drop policy if exists "recipe_ingredients: insert own (editor)" on public.recipe_ingredients;
create policy "recipe_ingredients: insert own (editor)"
on public.recipe_ingredients
for insert
to authenticated
with check (
  exists (
    select 1 from public.profiles p
    where p.id = auth.uid() and p.role = 'editor'
  )
  and exists (
    select 1 from public.recipes r
    where r.id = recipe_id and r.created_by = auth.uid()
  )
);

-- Editors can delete links ONLY for recipes they own
drop policy if exists "recipe_ingredients: delete own (editor)" on public.recipe_ingredients;
create policy "recipe_ingredients: delete own (editor)"
on public.recipe_ingredients
for delete
to authenticated
using (
  exists (
    select 1 from public.profiles p
    where p.id = auth.uid() and p.role = 'editor'
  )
  and exists (
    select 1 from public.recipes r
    where r.id = recipe_id and r.created_by = auth.uid()
  )
);
