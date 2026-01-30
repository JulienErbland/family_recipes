-- =========================
-- A) recipes.updated_at auto-update
-- Runs BEFORE UPDATE on public.recipes
-- =========================
create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_set_updated_at on public.recipes;
create trigger trg_set_updated_at
before update on public.recipes
for each row execute function public.set_updated_at();

-- =========================
-- B) auto-create profile on signup
-- Runs AFTER INSERT on auth.users
-- Default role = 'reader'
-- =========================
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, role)
  values (new.id, 'reader');
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();
