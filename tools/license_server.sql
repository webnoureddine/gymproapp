-- =====================================================================
--  GymPro DZ — LICENSE SERVER  (run ONCE in YOUR OWN Supabase project)
--  Supabase > SQL Editor > New query > paste everything > Run
--
--  This is NOT a gym database. It is your vendor database: one row per gym
--  that installed the app. You manage gyms in Table Editor > licenses.
-- =====================================================================

create table if not exists public.licenses (
  install_id   text primary key,
  gym_name     text,
  phone        text,
  city         text,
  status       text not null default 'trial' check (status in ('trial', 'active', 'suspended')),
  expires_at   date not null default (current_date + 14),   -- 14-day free trial
  message      text,                                         -- optional text shown to the gym
  notes        text,                                         -- your private notes (price, contact…)
  app_version  text,
  created_at   timestamptz not null default now(),
  last_seen    timestamptz
);

-- Nobody can read or write the table directly with the public key.
alter table public.licenses enable row level security;
revoke all on public.licenses from anon, authenticated;

-- The only thing the app can do: register itself / ask its status.
create or replace function public.check_license(
  p_install_id text, p_gym_name text default null, p_phone text default null,
  p_city text default null, p_version text default null)
returns json
language plpgsql
security definer
set search_path = public
as $$
declare r public.licenses;
begin
  if p_install_id is null or length(p_install_id) < 8 or length(p_install_id) > 20 then
    raise exception 'invalid install id';
  end if;
  insert into public.licenses (install_id, gym_name, phone, city, app_version, last_seen)
  values (upper(p_install_id), left(p_gym_name, 120), left(p_phone, 40), left(p_city, 80), left(p_version, 20), now())
  on conflict (install_id) do update
     set last_seen   = now(),
         gym_name    = coalesce(nullif(left(excluded.gym_name, 120), ''), licenses.gym_name),
         phone       = coalesce(nullif(left(excluded.phone, 40), ''), licenses.phone),
         city        = coalesce(nullif(left(excluded.city, 80), ''), licenses.city),
         app_version = excluded.app_version
  returning * into r;
  return json_build_object('status', r.status, 'expires_at', r.expires_at, 'message', r.message);
end $$;

revoke all on function public.check_license(text, text, text, text, text) from public;
grant execute on function public.check_license(text, text, text, text, text) to anon;

-- ---------------------------------------------------------------------
--  Useful queries (run them in SQL Editor when needed)
-- ---------------------------------------------------------------------
-- All gyms, newest first:
--   select install_id, gym_name, phone, city, status, expires_at, last_seen from licenses order by created_at desc;
-- A gym paid for 1 year:
--   update licenses set status = 'active', expires_at = current_date + 365 where install_id = '3F2A-91BC-04DE';
-- Give 7 more trial days:
--   update licenses set expires_at = expires_at + 7 where install_id = '3F2A-91BC-04DE';
-- Stop a gym immediately:
--   update licenses set status = 'suspended', message = 'Contactez-nous au 0550 12 34 56' where install_id = '3F2A-91BC-04DE';
-- Trials ending in the next 3 days (call them!):
--   select gym_name, phone, expires_at from licenses where status = 'trial' and expires_at <= current_date + 3;
