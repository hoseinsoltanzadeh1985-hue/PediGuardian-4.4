# Supabase migrations

Apply these migrations in timestamp order only after inspecting the target project's migration history and schema. Never assume a migration ran merely because it exists here. The webhook and Worker require the schema contract documented by these migrations.

All privileged SECURITY DEFINER RPCs are restricted to `service_role`; they must not be called by public clients.
