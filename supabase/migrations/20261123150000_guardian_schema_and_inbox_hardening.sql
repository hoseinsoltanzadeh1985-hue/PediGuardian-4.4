-- Bring the database contract into alignment with the 4.7.5 webhook and worker.
-- Existing members default to active; historical Telegram updates are considered
-- completed because earlier webhook versions inserted them before processing.
alter table public.members
  add column if not exists username text,
  add column if not exists display_name text,
  add column if not exists status text not null default 'active',
  add column if not exists warnings integer not null default 0;

alter table public.members
  drop constraint if exists members_status_check;
alter table public.members
  add constraint members_status_check
  check (status in ('active', 'restricted', 'banned'));

alter table public.members
  drop constraint if exists members_warnings_nonnegative_check;
alter table public.members
  add constraint members_warnings_nonnegative_check
  check (warnings >= 0);

create index if not exists members_group_role_idx
  on public.members (group_id, role);

alter table public.telegram_updates
  add column if not exists status text not null default 'PROCESSED',
  add column if not exists attempts integer not null default 0,
  add column if not exists lease_until timestamptz,
  add column if not exists lease_token uuid,
  add column if not exists processed_at timestamptz,
  add column if not exists last_error text;

alter table public.telegram_updates
  drop constraint if exists telegram_updates_status_check;
alter table public.telegram_updates
  add constraint telegram_updates_status_check
  check (status in ('PROCESSING', 'PROCESSED', 'FAILED'));

create index if not exists telegram_updates_status_lease_idx
  on public.telegram_updates (status, lease_until);

create or replace function public.claim_telegram_update(
  p_update_id bigint,
  p_lease_token uuid,
  p_lease_seconds integer default 120
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  claimed boolean := false;
  lease_seconds integer := GREATEST(30, LEAST(COALESCE(p_lease_seconds, 120), 600));
begin
  insert into public.telegram_updates as current_update (update_id, status, attempts, lease_until, lease_token, last_error)
  values (p_update_id, 'PROCESSING', 1, pg_catalog.now() + pg_catalog.make_interval(secs => lease_seconds), p_lease_token, null)
  on conflict (update_id) do update
     set status = 'PROCESSING',
         attempts = current_update.attempts + 1,
         lease_until = pg_catalog.now() + pg_catalog.make_interval(secs => lease_seconds),
         lease_token = p_lease_token,
         last_error = null
   where public.telegram_updates.status = 'FAILED'
      or (public.telegram_updates.status = 'PROCESSING' and public.telegram_updates.lease_until < pg_catalog.now())
  returning true into claimed;

  return COALESCE(claimed, false);
end;
$$;

revoke execute on function public.claim_telegram_update(bigint, uuid, integer) from public, anon, authenticated;
grant execute on function public.claim_telegram_update(bigint, uuid, integer) to service_role;

revoke execute on function public.claim_voice_order_request(bigint, text) from public, anon, authenticated;
revoke execute on function public.reclaim_expired_voice_order_requests() from public, anon, authenticated;
grant execute on function public.claim_voice_order_request(bigint, text) to service_role;
grant execute on function public.reclaim_expired_voice_order_requests() to service_role;

-- The tables are intended for trusted server-side use; do not add public or
-- authenticated policies here. Edge Functions/Worker use the service_role key.
