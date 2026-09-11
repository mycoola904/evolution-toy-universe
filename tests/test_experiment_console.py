from datetime import datetime, timezone

from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from experiment_console.app import create_app
from experiments.configuration import PRESETS_BY_SLUG


def form_values(**overrides):
    values = {
        name: str(value)
        for name, value in PRESETS_BY_SLUG["baseline"].form_values().items()
    }
    values.update({name: str(value) for name, value in overrides.items()})
    values["preset"] = "baseline"
    return values


def test_setup_history_reports_and_missing_run_routes(test_database_url):
    client = TestClient(create_app(database_url=test_database_url))

    setup = client.get("/")
    history = client.get("/runs")
    reports = client.get("/reports")
    missing = client.get("/runs/999999")

    assert setup.status_code == 200
    assert "Configure a universe" in setup.text
    assert "High Mutation" in setup.text
    assert history.status_code == 200
    assert "Run History" in history.text
    assert reports.status_code == 200
    assert "Longest-Lived Organisms" in reports.text
    assert missing.status_code == 404


def test_invalid_submission_returns_accessible_errors(test_database_url):
    client = TestClient(create_app(database_url=test_database_url))

    response = client.post(
        "/experiments",
        data=form_values(mutation_rate=2),
    )

    assert response.status_code == 422
    assert "mutation_rate must be between" in response.text
    assert 'role="alert"' not in response.text or "error" in response.text


def test_successful_submission_persists_and_redirects(test_database_url):
    client = TestClient(create_app(database_url=test_database_url))

    response = client.post(
        "/experiments",
        data=form_values(
            max_ticks=1,
            world_width=3,
            world_height=3,
            initial_organisms=1,
            regeneration_cell_count=0,
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303
    detail = client.get(response.headers["location"])
    assert detail.status_code == 200
    assert "Ticks completed" in detail.text
    assert "Organism lifespans" in detail.text
    assert "Full Experiment Report" in detail.text
    assert "Environmental Energy" in detail.text
    assert "Notable Organisms" in detail.text
    assert "Percentage of run" in detail.text

    run_id = int(response.headers["location"].rsplit("/", 1)[1])
    families = client.get(f"/runs/{run_id}/families")
    tree = client.get(f"/runs/{run_id}/families/0")
    assert families.status_code == 200
    assert "Lineage comparison" in families.text
    assert "Founder 0" in families.text
    assert tree.status_code == 200
    assert "Generation 0" in tree.text


def test_comparison_starts_empty_and_requires_two_selected_runs(
    test_database_url,
):
    client = TestClient(create_app(database_url=test_database_url))

    empty = client.get("/reports/comparison")
    response = client.get("/reports/comparison?run_id=1")

    assert empty.status_code == 200
    assert response.status_code == 422
    assert "Select at least two" in response.text


def test_legacy_run_without_report_json_renders_gracefully(
    database,
    test_database_url,
):
    with database.connect() as connection:
        run_id = connection.execute(
            """
            INSERT INTO simulation_runs (
                started_at, seed, world_width, world_height, ticks_completed,
                initial_organism_count, ending_organism_count,
                termination_reason, config_json, report_json
            ) VALUES (%s, 1, 1, 1, 0, 0, 0, 'extinction', %s, NULL)
            RETURNING id
            """,
            (datetime(2026, 9, 10, tzinfo=timezone.utc), Jsonb({})),
        ).fetchone()[0]

    response = TestClient(
        create_app(database_url=test_database_url)
    ).get(f"/runs/{run_id}")

    assert response.status_code == 200
    assert "Legacy run" in response.text
    assert "predates structured report persistence" in response.text


def test_family_tree_links_to_organism_genomes_and_parent_diffs(
    database,
    test_database_url,
):
    base_genome = {
        "reproduction_threshold": 150.0,
        "weights": {
            "WAIT": {"CELL_ENERGY": 0.5, "STORED_ENERGY": 0.2, "BIAS": -0.25},
            "EAT": {"CELL_ENERGY": 0.97, "STORED_ENERGY": 0.4, "BIAS": 0.1},
        },
    }
    mutated_genome = {
        **base_genome,
        "weights": {
            **base_genome["weights"],
            "EAT": {**base_genome["weights"]["EAT"], "CELL_ENERGY": 1.04},
        },
    }
    with database.connect() as connection:
        run_id = connection.execute(
            """
            INSERT INTO simulation_runs (
                started_at, seed, world_width, world_height, ticks_completed,
                initial_organism_count, ending_organism_count,
                termination_reason, config_json
            ) VALUES (%s, 4, 5, 5, 10, 1, 3, 'tick_limit', %s)
            RETURNING id
            """,
            (datetime(2026, 9, 10, tzinfo=timezone.utc), Jsonb({})),
        ).fetchone()[0]
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO organism_results (
                    simulation_run_id, organism_id, parent_organism_id,
                    birth_tick, mutated_weight_count, death_tick, lifespan,
                    initial_energy, final_energy, peak_energy,
                    energy_consumed, distance_moved, genome
                ) VALUES (%s, %s, %s, %s, %s, NULL, %s, 100, 80, 120, 12, 2, %s)
                """,
                (
                    (run_id, 100, None, 0, None, 10, Jsonb(base_genome)),
                    (run_id, 102, 100, 2, 1, 8, Jsonb(mutated_genome)),
                    (run_id, 103, 100, 3, 0, 7, Jsonb(base_genome)),
                ),
            )

    client = TestClient(create_app(database_url=test_database_url))
    tree = client.get(f"/runs/{run_id}/families/100")
    founder = client.get(f"/runs/{run_id}/organisms/100")
    mutated = client.get(f"/runs/{run_id}/organisms/102")
    unchanged = client.get(f"/runs/{run_id}/organisms/103")
    missing = client.get(f"/runs/{run_id}/organisms/999")

    assert tree.status_code == 200
    assert f'/runs/{run_id}/organisms/102' in tree.text
    assert founder.status_code == 200
    assert "Founder organism — no parent genome for comparison" in founder.text
    assert "0.97000000" in founder.text
    assert mutated.status_code == 200
    assert "1 mutated weight detected" in mutated.text
    assert "Parent genome" in mutated.text
    assert "EAT.CELL_ENERGY" in mutated.text
    assert "0.97000000" in mutated.text
    assert "1.04000000" in mutated.text
    assert "+0.07000000" in mutated.text
    assert f'/runs/{run_id}/organisms/100' in mutated.text
    assert f'/runs/{run_id}/organisms/103' in mutated.text
    assert unchanged.status_code == 200
    assert "Genome identical to parent" in unchanged.text
    assert missing.status_code == 404
