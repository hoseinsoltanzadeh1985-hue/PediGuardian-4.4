-- Give every voice queue claim a unique lease token.
-- Worker identity alone is not sufficient: an old process can restart with the
-- same WORKER_ID and otherwise complete a job claimed by its successor.
alter table public.voice_order_requests
  add column if not exists lease_token uuid;

create index if not exists voice_order_requests_lease_token_idx
  on public.voice_order_requests (lease_token)
  where lease_token is not null;

drop function if exists public.claim_voice_order_request(bigint, text);

create function public.claim_voice_order_request(p_id bigint, p_worker_id text)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  new_lease_token uuid;
begin
  update public.voice_order_requests
     set status = 'CLAIMED',
         worker_id = p_worker_id,
         claimed_at = pg_catalog.now(),
         lease_until = pg_catalog.now() + interval '5 minutes',
         lease_token = pg_catalog.gen_random_uuid()
   where id = p_id
     and (
       status = 'PENDING'
       or (status = 'CLAIMED' and lease_until <= pg_catalog.now())
     )
  returning lease_token into new_lease_token;

  return new_lease_token;
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
       set status = 'PENDING',
           worker_id = null,
           claimed_at = null,
           lease_until = null,
           lease_token = null
     where status = 'CLAIMED' and lease_until < pg_catalog.now()
    returning id
  )
  select pg_catalog.count(*)::integer from reclaimed;
$$;

revoke execute on function public.claim_voice_order_request(bigint, text) from public, anon, authenticated;
revoke execute on function public.reclaim_expired_voice_order_requests() from public, anon, authenticated;
grant execute on function public.claim_voice_order_request(bigint, text) to service_role;
grant execute on function public.reclaim_expired_voice_order_requests() to service_role;
