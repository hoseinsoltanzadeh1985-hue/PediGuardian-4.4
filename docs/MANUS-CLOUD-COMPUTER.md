# Manus Cloud Computer — voice worker deployment

## Purpose

This document describes the alternative to the Railway worker host. The Telegram webhook and database remain on Supabase. Only the persistent Python voice worker is moved to a Manus Cloud Computer.

Manus documents Cloud Computer as a persistent Ubuntu server that can keep applications, bots, and scripts running outside active Manus sessions. It is separate from the temporary task sandbox. Check the current plan, availability, and billing in your Manus account before provisioning; this package does not create a server.

## Worker details from this repository

- Docker build context: `worker/`
- Dockerfile: `worker/Dockerfile`
- Base image: Python 3.11 slim
- System package: FFmpeg
- Python dependencies: `worker/requirements.txt`
- Default HTTP health port: `8787`
- Health paths: `/health`, `/heartbeat`, `/live`
- Queue and heartbeat backend: Supabase

## Safe deployment sequence

1. In Manus, open Settings → My Computer and check whether a Cloud Computer is active. Create/provision one only after reviewing the current charges and confirming you want it.
2. Open its terminal or connect using the SSH details shown in your own Manus account. Do not put SSH credentials into GitHub or chat.
3. Clone the new repository you created from this package. Work from the repository's `worker/` directory.
4. Verify Docker is installed and available. If not, ask Manus to prepare a Python 3.11 virtual environment and FFmpeg, then configure a systemd service. Do not assume either method succeeded until tested.
5. Create a protected environment file outside the repository. Use `worker/.env.example` as the variable-name reference. Required values include `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `BOT_TOKEN`, `TG_API_ID`, `TG_API_HASH`, and `TG_SESSION_STRING`. Set file permissions so only the service account can read it.
6. Build from the `worker/` directory with that directory as the Docker build context. The included Dockerfile expects `requirements.txt` and `worker.py` relative to that context.
7. Run it with a persistent restart policy and configure startup after VM reboot. Do not store credentials in the Docker image.
8. Keep TCP port 8787 bound to localhost initially. The worker's health endpoint is for monitoring; do not publish it publicly unless the firewall and monitoring source are restricted.
9. Confirm the worker sends successful Supabase heartbeats and reaches ready state. Check logs for errors, but redact any values that might contain session or access credentials.
10. Test a development queue item before switching any production traffic.

## Example Docker layout (template only)

The following shows the build context and local-only health binding. Have Manus verify the actual Docker installation and environment file path before execution.

```bash
cd /path/to/PediGuardian/worker
docker build -t pedig-voice-worker:4.7.5 .
docker run -d \
  --name pedig-voice-worker \
  --restart unless-stopped \
  --env-file /secure/path/worker.env \
  -p 127.0.0.1:8787:8787 \
  pedig-voice-worker:4.7.5
```

If Docker is unavailable, do not paste secrets into a shell command. Use a protected environment file and a systemd unit with a restricted service account instead.

## Acceptance checks

- Container/service remains running after the Manus Cloud Computer session is closed.
- Service restarts after a controlled VM restart.
- `curl http://127.0.0.1:8787/health` returns a successful ready response only after Supabase heartbeat has succeeded.
- Worker can claim and complete a test queue item using its lease token.
- Supabase heartbeat age remains within the worker readiness threshold.
- No secret values appear in logs, source control, image layers, or public HTTP responses.

## Limitations

This worker host migration is not performed automatically by this ZIP. The current code does not prove that a specific Manus instance, firewall, or network configuration is available. Verify those details in the account before relying on it. Keep production traffic on the existing host until all acceptance checks pass.
