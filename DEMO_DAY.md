# Demo Day Runbook

Tested end-to-end on 2026-09-03: Docker build, `docker compose up`, health
checks, live queries on all 3 engines, 50-concurrent load, and full circuit-
breaker recovery — all verified against this exact procedure. See the
commit history around this date for the full verification log.

---

## Before you even open a terminal

Both of these auto-start when you log into Windows — confirmed on this
machine. You do not need to manually launch either one.

- **Docker Desktop** — registered in Windows Startup
- **Ollama** — registered in Windows Startup (serves Mistral on `:11434`)

Give the machine ~30–60 seconds after login before running anything, so
both have finished starting.

## The one command

```bash
cd sih-26117-agentic-workbench
docker compose up -d
```

That's it. This single command:
- builds the image if it isn't already built (first run only, ~1 min)
- starts both the API (`:8000`) and the Streamlit UI (`:8501`) in one container
- automatically finds and uses your host's Mistral GPU if Ollama is running,
  falls back to Gemini (if `GEMINI_API_KEY` is set in `.env`), then to the
  offline rule-based engine — in that order, with no config changes needed

## Confirm it's actually working (30 seconds)

```bash
curl http://localhost:8000/health
```

You want to see `"status": "OK"`. Check `"engine"` to see which one is
live — `"ollama"` means the local GPU model answered the last query,
`"gemini"` means cloud, `"rule-based"` means the deterministic fallback.
All three are valid; none of them means something is broken.

Then open **http://localhost:8501** in a browser and submit one of the
sample queries from the sidebar.

## For the jury: start with "How This Works"

Before diving into a live query, click the **🎬 How This Works** button at
the top of the page. It replaces the workbench with a self-contained,
animated walkthrough — the problem, the solution, the 5-agent pipeline, real-
world applications, and the economics — written for someone with zero
technical background. No network calls, no dependency on the API being up;
it's a static page that opens instantly. Click **← Back to the Workbench**
to return and run a real query.

## If something looks wrong

**`docker compose up` fails or hangs on build**
Docker Desktop isn't fully started yet. Wait 30s, retry. Check with
`docker info` — if that hangs too, Docker Desktop itself isn't ready.

**`/health` shows `"ollama": false` but you know Ollama is running**
Almost certainly not a Docker problem — this exact failure mode was found
and fixed today (`docker-compose.yml`'s `OLLAMA_BASE_URL` is hardcoded to
`host.docker.internal`, not read from `.env`). If you see this, someone
edited `docker-compose.yml`'s `environment:` block since — check it
against git history before troubleshooting further.

**A query takes 12+ seconds and gets a rule-based answer instead of ollama**
Not a bug — verified, expected behavior. Ollama serializes requests to the
one local GPU; if a previous query is still processing, or several judges
are trying it "at once," the new one waits, may hit its own timeout, and
safely falls back to a still-complete, still-correct answer. Nothing to
fix; this is the circuit breaker and orchestrator-level fallback doing
their job. `circuit_open` in `/health` will show `true` for up to 20
seconds after a burst, then self-heals on its own.

**Container shows unhealthy**
```bash
docker logs mrpl-workbench --tail 50
```
Was healthy within ~30s in every test today. If it's still starting after
a minute, something's actually wrong — check the log for a traceback.

**Port 8000 or 8501 already in use**
Something else on the machine (a leftover process from earlier testing,
most likely) is holding the port.
```bash
netstat -ano | findstr ":8000"
```
Find the PID in the last column, then `taskkill /PID <pid> /F` — but check
what it is first (`tasklist /FI "PID eq <pid>"`) so you don't kill
something unrelated.

## Shutting down afterward

```bash
docker compose down
```

Stops and removes the container cleanly. Nothing else needs to be touched —
Ollama and Docker Desktop can keep running in the background; they cost
nothing sitting idle, and starting the demo again next time is the same
one command.

## What NOT to do before/during the demo

- Don't run the 50-concurrent stress test (`scripts/stress_test.py`) right
  before or during a live demo — it deliberately hammers the local GPU and
  will trip the circuit breaker, meaning the next ~20s of *real* judge
  queries would answer via rule-based instead of ollama. Harmless, but
  needlessly hides your best result if a judge is watching that moment.
- Don't `docker system prune` or touch other images/containers on this
  machine right before demo day without checking what they are first —
  see the git history around 2026-09-03 for what's safe vs. what belongs
  to unrelated projects on this machine.
