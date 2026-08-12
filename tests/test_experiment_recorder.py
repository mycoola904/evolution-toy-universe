import json
import sqlite3
from datetime import datetime, timezone

import pytest

from domain.action import Action
from domain.sensor import Sensor
from domain.simulation import Simulation
from experiments.results import (
    ExperimentResult,
    OrganismResult,
    SimulationRunResult,
    build_experiment_result,
)
from persistence.database import ExperimentDatabase
from persistence.experiment_recorder import ExperimentRecorder


def make_run_result(**overrides) -> SimulationRunResult:
    values = {
        "started_at": "2026-08-12T12:00:00+00:00",
        "seed": 42,
        "world_width": 5,
        "world_height": 5,
        "ticks_completed": 3,
        "initial_organism_count": 1,
        "ending_organism_count": 1,
        "termination_reason": "tick_limit",
        "config": {"seed": 42, "world_width": 5},
        "git_commit": "abc123",
        "git_dirty": False,
    }
    values.update(overrides)
    return SimulationRunResult(**values)


def make_organism_result(**overrides) -> OrganismResult:
    values = {
        "organism_id": 0,
        "parent_organism_id": None,
        "birth_tick": 0,
        "death_tick": None,
        "lifespan": 3,
        "initial_energy": 100.0,
        "final_energy": 75.0,
        "peak_energy": 110.0,
        "energy_consumed": 12.0,
        "distance_moved": 2,
        "genome": {
            "reproduction_threshold": 150.0,
            "weights": {},
        },
    }
    values.update(overrides)
    return OrganismResult(**values)


def test_recorder_saves_run_and_multiple_organisms(tmp_path):
    database = ExperimentDatabase(tmp_path / "experiments.db")
    database.initialize()
    result = ExperimentResult(
        run=make_run_result(git_dirty=None, git_commit=None),
        organisms=(
            make_organism_result(),
            make_organism_result(
                organism_id=1,
                parent_organism_id=0,
                birth_tick=2,
                lifespan=1,
                initial_energy=50.0,
                final_energy=50.0,
            ),
        ),
    )

    run_id = ExperimentRecorder(database).save(result)

    with database.connect() as connection:
        connection.row_factory = sqlite3.Row
        run = connection.execute(
            "SELECT * FROM simulation_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        organisms = connection.execute(
            """
            SELECT * FROM organism_results
            WHERE simulation_run_id = ?
            ORDER BY organism_id
            """,
            (run_id,),
        ).fetchall()

    assert run is not None
    assert run["termination_reason"] == "tick_limit"
    assert json.loads(run["config_json"]) == result.run.config
    assert run["git_commit"] is None
    assert run["git_dirty"] is None
    assert len(organisms) == 2
    assert organisms[0]["parent_organism_id"] is None
    assert organisms[1]["parent_organism_id"] == 0
    assert json.loads(organisms[0]["genome"]) == result.organisms[0].genome


def test_recorder_rolls_back_the_whole_experiment(tmp_path):
    database = ExperimentDatabase(tmp_path / "experiments.db")
    database.initialize()
    duplicate = make_organism_result()
    result = ExperimentResult(
        run=make_run_result(),
        organisms=(duplicate, duplicate),
    )

    with pytest.raises(sqlite3.IntegrityError):
        ExperimentRecorder(database).save(result)

    with database.connect() as connection:
        run_count = connection.execute(
            "SELECT COUNT(*) FROM simulation_runs"
        ).fetchone()[0]
        organism_count = connection.execute(
            "SELECT COUNT(*) FROM organism_results"
        ).fetchone()[0]

    assert run_count == 0
    assert organism_count == 0


def force_action(organism, selected_action: Action) -> None:
    for action in Action:
        for sensor in Sensor:
            organism.genome.weights[action][sensor] = 0.0
    organism.genome.weights[selected_action][Sensor.BIAS] = 1.0


def test_completed_snapshot_and_recorder_include_dead_organism(
    config_factory,
    tmp_path,
):
    simulation = Simulation.big_bang(
        config_factory(
            initial_organism_energy=1.0,
            initial_reproduction_threshold=1_000.0,
            base_energy_cost_per_tick=2.0,
        )
    )
    for cell in simulation.world.cells:
        cell.energy = 0.0
    simulation.initial_world_energy = 0.0
    force_action(simulation.organisms[0], Action.WAIT)
    simulation.step()
    random_state = simulation.random.getstate()
    result = build_experiment_result(
        simulation=simulation,
        started_at=datetime(2026, 8, 12, tzinfo=timezone.utc),
        git_commit="abc123",
        git_dirty=True,
    )

    assert simulation.random.getstate() == random_state
    assert result.run.termination_reason == "extinction"
    assert result.run.ending_organism_count == 0
    assert result.run.config["base_energy_cost_per_tick"] == 2.0
    assert len(result.organisms) == 1
    organism = result.organisms[0]
    assert organism.death_tick == 1
    assert organism.lifespan == 1
    assert organism.initial_energy == 1.0
    assert organism.final_energy == 0.0

    database = ExperimentDatabase(tmp_path / "experiments.db")
    database.initialize()
    run_id = ExperimentRecorder(database).save(result)

    with database.connect() as connection:
        stored = connection.execute(
            """
            SELECT death_tick, lifespan, initial_energy, final_energy
            FROM organism_results
            WHERE simulation_run_id = ?
            """,
            (run_id,),
        ).fetchone()

    assert stored == (1, 1, 1.0, 0.0)


def test_completed_snapshot_preserves_reproduction_lineage(config_factory):
    simulation = Simulation.big_bang(config_factory())
    for cell in simulation.world.cells:
        cell.energy = 0.0
    simulation.initial_world_energy = 0.0
    force_action(simulation.organisms[0], Action.WAIT)

    simulation.step()
    result = build_experiment_result(
        simulation=simulation,
        started_at=datetime(2026, 8, 12, tzinfo=timezone.utc),
        git_commit=None,
        git_dirty=None,
    )

    assert result.run.termination_reason == "tick_limit"
    assert [item.organism_id for item in result.organisms] == [0, 1]
    assert result.organisms[0].parent_organism_id is None
    assert result.organisms[1].parent_organism_id == 0
    assert result.organisms[0].final_energy == 50.0
    assert result.organisms[1].initial_energy == 50.0
