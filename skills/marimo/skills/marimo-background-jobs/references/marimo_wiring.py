"""marimo glue for background jobs — the status panel + the reactive cells.

Distilled from MetaboStatsHub `src/cd_convert/apps/job_status.py` and the run/inspect cells of
`src/cd_convert/apps/app.py`. Pairs with references/jobrunner.py (imported here as `runner`).

Two parts:
  1. build_status_panel(status, ...) — a plain function returning an mo.callout.
  2. A marimo-cell template (commented) showing the state, refresh widget, and run+inspect cell.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import marimo as mo

import jobrunner as runner  # your project's copy of references/jobrunner.py


def build_status_panel(
    status: runner.JobStatus,
    *,
    refresh_widget: object,
    get_server: Callable[[], runner.StaticServer | None],
    set_server: Callable[[runner.StaticServer | None], None],
    report_label: str = "Open report",
    download_filename: str = "results.zip",
    zip_exclude_suffixes: tuple[str, ...] = (),
    max_log_chars: int = 6000,
) -> mo.Html:
    """Render the Running / Finished / Failed callout with a live log tail and links."""
    if status.running:
        state_label, kind = "Running…", "info"
    elif status.success:
        state_label, kind = "Finished (exit 0)", "success"
    else:
        state_label, kind = f"Failed (exit {status.returncode})", "danger"

    items: list[object] = [
        mo.md(f"**Status:** {state_label}"),
        mo.md(f"Output: `{status.output_dir}`"),
        mo.md(f"Log: `{status.log_file}`"),
    ]

    if not status.running and status.output_dir.exists():
        # Report links only on success (rglob can match a stale prior report); the .zip
        # download stays available even on failure so the log is always grabbable.
        if status.success and status.reports:
            server = get_server()
            if server is None or not server.running or server.root_dir != status.output_dir.resolve():
                if server is not None and server.running:
                    server.process.terminate()
                server = runner.start_static_server(status.output_dir)
                set_server(server)
            for report in status.reports:
                items.append(mo.md(f"📊 **[{report_label}]({runner.path_to_url(report, server)})**"))
            items.append(mo.md(f"📁 [Open output folder]({server.base_url}/)"))
        items.append(
            mo.download(
                data=lambda: runner.zip_dir_to_bytes(status.output_dir, zip_exclude_suffixes),
                filename=download_filename,
                label="Download results (.zip)",
            )
        )

    if status.running:
        items.append(refresh_widget)            # only poll while running

    log_text = status.log_text or "*(no log output yet)*"
    items.append(mo.accordion({"Console log": mo.md(f"```\n{log_text[-max_log_chars:]}\n```")}, lazy=False))
    return mo.callout(mo.vstack(items, gap=0.4), kind=kind)


# ──────────────────────────────────────────────────────────────────────────────────────────
# marimo cells (copy into your `app.py`; each `@app.cell` is a separate cell)
# ──────────────────────────────────────────────────────────────────────────────────────────
#
# @app.cell
# def _(mo):
#     get_job, set_job = mo.state(None)        # the Job handle
#     get_server, set_server = mo.state(None)  # the StaticServer
#     get_done, set_done = mo.state(None)      # run_key of a job already seen finished
#     run_button = mo.ui.run_button(label="Run ▶")
#     return get_job, set_job, get_server, set_server, get_done, set_done, run_button
#
# @app.cell
# def _(get_done, get_job, mo):
#     # Auto-poll ONLY while a job runs. Read state getters (not graph vars) so this cell
#     # stays outside the run cell's dependency cycle. Depending on get_done() rebuilds this
#     # widget with auto-poll OFF once the process exits.
#     get_done()
#     _job = get_job()
#     _running = _job is not None and _job.process.poll() is None
#     log_refresh = mo.ui.refresh(options=["1s", "2s", "5s", "10s"],
#                                 default_interval="2s" if _running else None, label="Refresh log")
#     return (log_refresh,)
#
# @app.cell
# def _(run_button, log_refresh, get_job, set_job, get_done, set_done,
#       get_server, set_server, runner, mo, build_status_panel, /* your inputs */):
#     import sys
#     job = get_job()
#     run_key = runner.make_run_key(/* the inputs that define this run */)
#     if job is not None and job.run_key != run_key:        # selection changed → don't orphan
#         runner.terminate_job(job); set_job(None); job = None
#     running = job is not None and job.process.poll() is None
#     if run_button.value and not running:                  # start once per click, when idle
#         cmd = [sys.executable, "-m", "yourpkg.worker", /* args, e.g. paths */]
#         job = runner.start_job(cmd, output_dir, log_file=output_dir / "console.log",
#                                run_key=run_key)
#         set_job(job)
#     if job is None:
#         panel = mo.md("*Click Run to start.*")
#     else:
#         _ = log_refresh.value                             # depend on the tick → re-inspect
#         status = runner.inspect_job(job, report_glob="report.html")
#         if not status.running and get_done() != job.run_key:
#             set_done(job.run_key)                         # flag finished ONCE (run_key-guarded)
#         panel = build_status_panel(status, refresh_widget=log_refresh,
#                                    get_server=get_server, set_server=set_server)
#     panel
#     return (panel,)
#
# ──────────────────────────────────────────────────────────────────────────────────────────
# Container deployment (one HTTP port, no per-run servers): serve outputs via FastAPI.
# In web_app.py:
#   server = marimo.create_asgi_app().with_app(path="/", root=str(APP_PY))
#   app = FastAPI()
#   app.mount("/reports", StaticFiles(directory=str(output_root), html=True))  # BEFORE "/"
#   app.mount("/", server.build())
# Then build_status_panel links to f"/reports/<rel path>" when an env var (e.g.
# REPORT_BASE_URL) is set, instead of starting start_static_server().
