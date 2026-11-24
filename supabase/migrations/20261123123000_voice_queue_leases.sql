alter table public.voice_order_requests
  add column if not exists claimed_at timestamptz,
  add column if not exists lease_until timestamptz;

create index if not exists voice_order_requests_claimed_idx
  on public.voice_order_requests (status, lease_until);

create or replace function public.claim_voice_order_request(p_id bigint, p_worker_id text)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  claimed integer := 0;
begin
  update public.voice_order_requests
     set status = 'CLAIMED',
         worker_id = p_worker_id,
         claimed_at = pg_catalog.now(),
         lease_until = pg_catalog.now() + interval '5 minutes'
   where id = p_id
     and (
       status = 'PENDING'
       or (status = 'CLAIMED' and lease_until < pg_catalog.now())
       or (status = 'CLAIMED' and worker_id = p_worker_id and lease_until > pg_catalog.now())
     );
  get diagnostics claimed = row_count;
  return claimed = 1;
end;
$$;

create or replace function public.reclaim_expired_voice_order_requests()
returns integer
language sql
security definer
set search_path = ''
as $$
  with reclaimed as (
    update public.voice_order_requests
       set status = 'PENDING', worker_id = null, claimed_at = null, lease_until = null
     where status = 'CLAIMED' and lease_until < pg_catalog.now()
    returning id
  )
  select pg_catalog.count(*)::integer from reclaimed;
$$;

revoke execute on function public.claim_voice_order_request(bigint, text) from public, anon, authenticated;
revoke execute on function public.reclaim_expired_voice_order_requests() from public, anon, authenticated;
grant execute on function public.claim_voice_order_request(bigint, text) to service_role;
grant execute on function public.reclaim_expired_voice_order_requests() to service_role;
