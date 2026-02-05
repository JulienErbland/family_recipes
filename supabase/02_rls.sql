alter table public.profiles enable row level security;
alter table public.recipes enable row level security;
alter table public.ingredients enable row level security;
alter table public.recipe_ingredients enable row level security;

alter table public.recipe_seasons enable row level security;

-- Any logged-in user can read recipe seasons
drop policy if exists "recipe_seasons: read all" on public.recipe_seasons;
create policy "recipe_seasons: read all"
on public.recipe_seasons
for select
to authenticated
using (true);

-- Editors can add seasons only for recipes they own
drop policy if exists "recipe_seasons: insert own (editor)" on public.recipe_seasons;
create policy "recipe_seasons: insert own (editor)"
on public.recipe_seasons
for insert
to authenticated
with check (
  exists (select 1 from public.profiles p where p.id = auth.uid() and p.role = 'editor')
  and exists (select 1 from public.recipes r where r.id = recipe_id and r.created_by = auth.uid())
);

-- Editors can delete seasons only for recipes they own
drop policy if exists "recipe_seasons: delete own (editor)" on public.recipe_seasons;
create policy "recipe_seasons: delete own (editor)"
on public.recipe_seasons
for delete
to authenticated
using (
  exists (select 1 from public.profiles p where p.id = auth.uid() and p.role = 'editor')
  and exists (select 1 from public.recipes r where r.id = recipe_id and r.created_by = auth.uid())
);
