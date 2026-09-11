import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from experiment_console.forms import (
    FORM_FIELDS,
    config_form_values,
    parse_experiment_form,
)
from experiments.configuration import PRESETS, PRESETS_BY_SLUG
from experiments.runner import ExperimentRunner
from persistence.database import DatabaseConfigurationError, ExperimentDatabase, PROJECT_ROOT
from persistence.reports import ExperimentReports


CONSOLE_ROOT = Path(__file__).resolve().parent


def create_app(
    *,
    database_url: str | None = None,
    runner: ExperimentRunner | None = None,
    reports: ExperimentReports | None = None,
) -> FastAPI:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    connection_info = database_url or os.environ.get("DATABASE_URL")
    if connection_info is None or not connection_info.strip():
        raise DatabaseConfigurationError(
            "DATABASE_URL must be set to start the Experiment Console"
        )

    app = FastAPI(title="Evolution Toy Universe Experiment Console")
    templates = Jinja2Templates(directory=CONSOLE_ROOT / "templates")
    app.mount(
        "/static",
        StaticFiles(directory=CONSOLE_ROOT / "static"),
        name="static",
    )
    experiment_runner = runner or ExperimentRunner()
    if reports is None:
        database = ExperimentDatabase(connection_info)
        database.initialize()
        experiment_reports = ExperimentReports(database)
    else:
        experiment_reports = reports

    def setup_context(
        request: Request,
        *,
        values: dict[str, str],
        selected_preset: str,
        errors: dict[str, str] | None = None,
    ) -> dict:
        sections: dict[str, list] = {}
        for field in FORM_FIELDS:
            sections.setdefault(field.section, []).append(field)
        return {
            "request": request,
            "values": values,
            "selected_preset": selected_preset,
            "presets": PRESETS,
            "sections": sections,
            "errors": errors or {},
        }

    @app.get("/", response_class=HTMLResponse, name="experiment_setup")
    async def experiment_setup(
        request: Request,
        preset: str = "baseline",
    ) -> HTMLResponse:
        selected = PRESETS_BY_SLUG.get(preset, PRESETS_BY_SLUG["baseline"])
        return templates.TemplateResponse(
            request=request,
            name="setup.html",
            context=setup_context(
                request,
                values=config_form_values(selected.config()),
                selected_preset=selected.slug,
            ),
        )

    @app.post("/experiments", response_class=HTMLResponse)
    async def run_experiment(request: Request) -> HTMLResponse:
        submitted = await request.form()
        values = {key: str(value) for key, value in submitted.items()}
        result = parse_experiment_form(values)
        selected_preset = values.get("preset", "baseline")
        if result.config is None:
            return templates.TemplateResponse(
                request=request,
                name="setup.html",
                context=setup_context(
                    request,
                    values=result.values,
                    selected_preset=selected_preset,
                    errors=result.errors,
                ),
                status_code=422,
            )

        outcome = await run_in_threadpool(
            experiment_runner.run,
            result.config,
            database_url=connection_info,
            persist=True,
        )
        if outcome.run_id is None:
            raise RuntimeError("Experiment completed without a persisted run ID")
        return RedirectResponse(
            url=f"/runs/{outcome.run_id}",
            status_code=303,
        )

    @app.get("/runs", response_class=HTMLResponse, name="run_history")
    async def run_history(request: Request) -> HTMLResponse:
        runs = await run_in_threadpool(experiment_reports.recent_runs, 100)
        return templates.TemplateResponse(
            request=request,
            name="history.html",
            context={"request": request, "runs": runs},
        )

    @app.get("/runs/{run_id}", response_class=HTMLResponse, name="run_detail")
    async def run_detail(request: Request, run_id: int) -> HTMLResponse:
        detail = await run_in_threadpool(experiment_reports.run_detail, run_id)
        if detail is None:
            return templates.TemplateResponse(
                request=request,
                name="not_found.html",
                context={"request": request, "run_id": run_id},
                status_code=404,
            )
        distribution = await run_in_threadpool(
            experiment_reports.lifespan_distribution,
            run_id,
        )
        chart_data = {}
        for alive_at_end, key in ((False, "died"), (True, "alive")):
            matching = [
                row
                for row in distribution
                if row["alive_at_end"] is alive_at_end
            ]
            chart_data[key] = {
                "lifespans": [row["lifespan"] for row in matching],
                "counts": [row["organism_count"] for row in matching],
                "percentages": [row["percentage"] for row in matching],
            }
        return templates.TemplateResponse(
            request=request,
            name="run_detail.html",
            context={
                "request": request,
                "run": detail,
                "distribution": distribution,
                "chart_data": json.dumps(chart_data),
            },
        )

    @app.get(
        "/runs/{run_id}/families",
        response_class=HTMLResponse,
        name="run_families",
    )
    async def run_families(request: Request, run_id: int) -> HTMLResponse:
        detail = await run_in_threadpool(experiment_reports.run_detail, run_id)
        if detail is None:
            return templates.TemplateResponse(
                request=request,
                name="not_found.html",
                context={"request": request, "run_id": run_id},
                status_code=404,
            )
        families = await run_in_threadpool(
            experiment_reports.family_summaries,
            run_id,
        )
        return templates.TemplateResponse(
            request=request,
            name="families.html",
            context={
                "request": request,
                "run": detail,
                "families": families,
            },
        )

    @app.get(
        "/runs/{run_id}/families/{founder_id}",
        response_class=HTMLResponse,
        name="family_tree",
    )
    async def family_tree(
        request: Request,
        run_id: int,
        founder_id: int,
    ) -> HTMLResponse:
        detail = await run_in_threadpool(experiment_reports.run_detail, run_id)
        tree = await run_in_threadpool(
            experiment_reports.family_tree,
            run_id,
            founder_id,
        )
        if detail is None or tree is None:
            return templates.TemplateResponse(
                request=request,
                name="family_not_found.html",
                context={
                    "request": request,
                    "run_id": run_id,
                    "founder_id": founder_id,
                },
                status_code=404,
            )
        return templates.TemplateResponse(
            request=request,
            name="family_tree.html",
            context={"request": request, "run": detail, "tree": tree},
        )

    @app.get("/reports", response_class=HTMLResponse, name="reports")
    async def reports_page(request: Request) -> HTMLResponse:
        recent = await run_in_threadpool(experiment_reports.recent_runs, 10)
        leaderboards = {}
        for metric in (
            "lifespan",
            "peak_energy",
            "energy_consumed",
            "distance_moved",
        ):
            leaderboards[metric] = await run_in_threadpool(
                experiment_reports.leaderboard,
                metric,
                10,
            )
        return templates.TemplateResponse(
            request=request,
            name="reports.html",
            context={
                "request": request,
                "recent_runs": recent,
                "leaderboards": leaderboards,
            },
        )

    @app.get(
        "/reports/comparison",
        response_class=HTMLResponse,
        name="run_comparison",
    )
    async def run_comparison(request: Request) -> HTMLResponse:
        raw_ids = request.query_params.getlist("run_id")
        error = None
        compared_runs = []
        if raw_ids:
            try:
                run_ids = [int(run_id) for run_id in raw_ids]
                compared_runs = await run_in_threadpool(
                    experiment_reports.compare_runs,
                    run_ids,
                )
                if len(compared_runs) < 2:
                    error = "Two saved runs must exist and be selected."
            except (ValueError, TypeError):
                error = "Select at least two different saved runs to compare."
        recent = await run_in_threadpool(experiment_reports.recent_runs, 100)
        return templates.TemplateResponse(
            request=request,
            name="comparison.html",
            context={
                "request": request,
                "runs": recent,
                "selected_ids": raw_ids,
                "compared_runs": compared_runs,
                "error": error,
            },
            status_code=422 if error else 200,
        )

    return app
