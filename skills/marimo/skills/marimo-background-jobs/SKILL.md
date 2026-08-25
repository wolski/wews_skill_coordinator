---
name: marimo-background-jobs
description: >
  This skill should be used when a marimo app (or Python data GUI) must run a long-running or
  memory-heavy task and show live progress and logs without freezing the UI. Trigger phrases:
  "show a progress/log panel in marimo", "stream a job's log while it runs", "run the
  conversion/render/analysis in the background", "poll a job with mo.ui.refresh", "open the
  generated report or log file in the browser from marimo", "my marimo button blocks the UI",
  or "the data:/file: log link does not open". Covers the background-subprocess + log-file +
  refresh-polling + status-callout pattern, including process-group cleanup and serving outputs
  over a real static HTTP server.
---

# Background jobs with live logs in marimo

Run heavy work as a **background subprocess** that streams stdout/stderr to a **log file**; let
the marimo UI **poll** with `mo.ui.refresh`, **tail** the log each tick, and render a **status
callout** (Running / Finished / Failed) with the live log, the log path, a results download, and
report links served by a **real static HTTP server**. This keeps the marimo server responsive,
shows genuine progress, and produces links that actually open in a browser.

The production reference is MetaboStatsHub (`prolfqua_fml/MetaboStatsHub`):
`src/cd_convert/prolfqua_runner.py` (pure machinery) and `src/cd_convert/apps/job_status.py`
plus the run/inspect cells in `src/cd_convert/apps/app.py` (marimo glue). Distilled,
project-agnostic copies are in [references/jobrunner.py](references/jobrunner.py) and
[references/marimo_wiring.py](references/marimo_wiring.py).

## Why this pattern (and what it replaces)

Avoid these anti-patterns, which the pattern exists to fix:

- **Synchronous work inside a cell** (`obj = convert(...)` on button click). It blocks the marimo
  event loop: the spinner never updates, the user cannot tell if it is working or hung, and a
  multi-GB job freezes the whole app. Move the work to a subprocess.
- **`file://` log/report links.** Browsers block navigating to `file://` from an `http://` page;
  the link silently does nothing.
- **`data:text/html` links.** Chrome blocks top-level navigation to `data:text/html` (anti-
  phishing), so "open in new tab" fails. `data:text/plain` works only for tiny inline text and
  never updates live. Serve files over HTTP instead.

## Architecture: two layers

Keep the machinery free of any `marimo` import so it is unit-testable; the marimo file is thin glue.

1. **Pure runner** (no marimo) — start/inspect/tail/terminate a subprocess, serve outputs, zip
   outputs. See `references/jobrunner.py`.
2. **marimo glue** — `mo.state` for the job handle, an `mo.ui.refresh` widget that auto-polls only
   while running, a run+inspect cell, and a `build_status_panel(status, ...)` renderer. See
   `references/marimo_wiring.py`.

## Layer 1 — the runner

- **`start_job(command, output_dir, log_file, run_key)` → `Job`**: open the log file, write the
  command line, launch `subprocess.Popen(cmd, stdout=handle, stderr=STDOUT, text=True)`. Start the
  child in **its own process group/session** (`start_new_session=True` on POSIX,
  `creationflags=CREATE_NEW_PROCESS_GROUP` on Windows) so the whole tree can be killed later.
  Record `run_key`, `started_at`, and a snapshot of pre-existing output files.
- **`inspect_job(job, report_glob, max_log_chars)` → `JobStatus`** (pure read, no side effects):
  `returncode = job.process.poll()`; `running = returncode is None`; `log_text =
  read_text_tail(job.log_file, max_log_chars)`; discover fresh report files under `output_dir`.
- **`read_text_tail(path, max_log_chars)`**: read a UTF-8 file with `errors="replace"`; if longer
  than the cap, return `"... log truncated ...\n" + text[-max_log_chars:]`. Never load a giant log.
- **`terminate_job(job)`**: signal the child's **process group** (`os.killpg` / `taskkill /T`),
  wait, then escalate (`SIGKILL` / `taskkill /T /F`). Call this when inputs change so a stale run
  cannot keep writing to the output dir (the GUI is about to drop the only handle to it).
- **`start_static_server(root_dir)`**: `find_available_port()` then spawn
  `python -m http.server <port> --bind 127.0.0.1 --directory <root>`; `path_to_url(path, server)`
  maps a file under root to `http://host:port/<url-quoted relative path>`. This is how reports/logs
  open in the browser — a real HTTP origin, not `file://`/`data:`.
- **`zip_dir_to_bytes(dir, exclude_suffixes)`**: in-memory zip for `mo.download` so the user can
  grab the whole output folder (logs included) regardless of success.
- **`make_run_key(*parts)`**: a `hashlib.sha256` fingerprint of the inputs that define a run. A
  changed key means "the selection changed" → terminate the stale job and reset the panel.

## Layer 2 — the marimo wiring

Three pieces of `mo.state` (define each in its own cell, return the getter/setter):

- the **job handle** (`get_job/set_job`), initial `None`;
- the **static server** (`get_server/set_server`), initial `None`;
- a **done token** (`get_done/set_done`) holding the `run_key` of a job already observed finished.

**Refresh widget cell** — auto-poll only while running:

```python
@app.cell
def _(get_done, get_job, mo):
    get_done()                                   # depend on the token → rebuild when job ends
    _job = get_job()
    _running = _job is not None and _job.process.poll() is None
    log_refresh = mo.ui.refresh(
        options=["1s", "2s", "5s", "10s"],
        default_interval="2s" if _running else None,   # None = no auto-poll when idle/done
        label="Refresh log",
    )
    return (log_refresh,)
```

Read the **state getters** here, not graph variables, so this cell stays *outside* the run cell's
dependency cycle (otherwise marimo cannot order the graph).

**Run + inspect + panel cell**:

```python
@app.cell
def _(run_button, log_refresh, get_job, set_job, get_done, set_done,
      get_server, set_server, runner, job_status, mo, /* inputs */):
    job = get_job()
    run_key = runner.make_run_key(/* the inputs that define this run */)

    if job is not None and job.run_key != run_key:   # selection changed
        runner.terminate_job(job); set_job(None); job = None

    running = job is not None and job.process.poll() is None
    if run_button.value and not running:             # start once per click, if idle
        cmd = [sys.executable, "-m", "yourpkg.worker", ...]   # the heavy work as a subprocess
        job = runner.start_job(cmd, output_dir, log_file=output_dir / "console.log",
                               run_key=run_key)
        set_job(job)

    if job is None:
        panel = mo.md("*Click Run to start.*")
    else:
        _ = log_refresh.value                        # depend on the tick → re-inspect each poll
        status = runner.inspect_job(job, report_glob="report.html")
        if not status.running and get_done() != job.run_key:
            set_done(job.run_key)                    # flag finished ONCE (run_key-guarded)
        panel = job_status.build_status_panel(status, refresh_widget=log_refresh,
                                              get_server=get_server, set_server=set_server)
    return (panel,)
```

`build_status_panel` returns an `mo.callout(kind="info"|"success"|"danger")` containing: the status
label, `Output: <dir>`, `Log: <log_file>`, the live log tail in an `mo.accordion`, the
`refresh_widget` (only while running), a `mo.download` zip, and report links (only on success). See
`references/marimo_wiring.py`.

## Critical gotchas (the hard-won bits)

- **Poll only while running.** Set `default_interval=None` when idle/finished, else the app polls
  forever and re-renders endlessly.
- **Stop polling cleanly.** A subprocess exiting does **not** wake marimo. The inspect cell detects
  the exit and sets a **done token**; the refresh cell depends on that token and rebuilds with
  auto-poll off. Guard the `set_done` with the `run_key` so the rebuild re-run does not set it again
  (infinite loop).
- **Never `mo.stop()` in a cell whose output the layout needs** — on first load it halts before
  defining the output and the page fails to render. Use conditionals + state instead.
- **Kill the whole tree.** Start the child in its own group/session and signal the group; otherwise
  a wrapper that spawned R/quarto/etc. leaves orphans.
- **Terminate stale jobs on input change** (via `run_key`) before dropping the handle.
- **Serve, don't link files.** Use the static HTTP server (desktop) or, in a container, a single
  reverse-proxied `StaticFiles` mount gated by an env var
  (`marimo.create_asgi_app()` under FastAPI, reports mounted at `/reports` *before* the marimo
  catch-all at `/`). See `references/marimo_wiring.py` and MetaboStatsHub `apps/web_app.py`.

## Subprocess vs thread

Prefer a **subprocess**: non-blocking, hard-killable, isolates crashes/memory, and `poll()`/log-file
polling is trivial. Make the worker a `python -m yourpkg.worker` module that writes to stdout. If the
work is unavoidably in-process, a background **thread** writing to a log file is a fallback, but it
cannot be force-killed and shares the GIL — note this limitation.

## Testing

The pure runner is fully unit-testable with fakes: inject a fake `popen`/`run`; assert `read_text_tail`
truncation, `inspect_job` running/finished transitions (`poll()` returning `None` then `0`/non-zero),
and that a running panel shows the refresh widget and no download while a finished panel shows the
download. The panel renders from a plain `JobStatus`, so assert on its structure without a browser.
See MetaboStatsHub `tests/test_prolfqua_runner.py` and `tests/test_job_status.py`.
