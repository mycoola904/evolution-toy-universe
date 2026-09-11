from experiments.organism_inspection import (
    compare_persisted_genomes,
    inspect_organism,
)


def genome(*, eat_cell_energy=0.97, wait_bias=-0.25):
    return {
        "reproduction_threshold": 150.0,
        "weights": {
            "WAIT": {"CELL_ENERGY": 0.5, "STORED_ENERGY": 0.2, "BIAS": wait_bias},
            "EAT": {"CELL_ENERGY": eat_cell_energy, "STORED_ENERGY": 0.4, "BIAS": 0.1},
        },
    }


def row(
    organism_id,
    parent_id,
    persisted_genome,
    mutated_weight_count,
    *,
    birth_tick=0,
):
    return {
        "simulation_run_id": 7,
        "organism_id": organism_id,
        "parent_organism_id": parent_id,
        "birth_tick": birth_tick,
        "mutated_weight_count": mutated_weight_count,
        "death_tick": None,
        "lifespan": 12 - birth_tick,
        "initial_energy": 100.0,
        "final_energy": 80.0,
        "peak_energy": 120.0,
        "energy_consumed": 10.0,
        "distance_moved": 3,
        "genome": persisted_genome,
    }


def family_rows():
    founder_genome = genome()
    return [
        row(10, None, founder_genome, None),
        row(11, 10, genome(eat_cell_energy=1.04), 1, birth_tick=2),
        row(12, 10, genome(), 0, birth_tick=3),
        row(13, 11, genome(eat_cell_energy=1.04), 0, birth_tick=5),
    ]


def test_identical_descendant_has_no_changed_weights():
    comparison = compare_persisted_genomes(
        genome(), genome(), recorded_mutated_weight_count=0
    )

    assert comparison.identical is True
    assert comparison.changed_weight_count == 0
    assert comparison.recorded_count_matches is True


def test_one_mutation_identifies_exact_weight_and_numeric_delta():
    comparison = compare_persisted_genomes(
        genome(), genome(eat_cell_energy=1.04), recorded_mutated_weight_count=1
    )

    assert comparison.identical is False
    assert comparison.changed_weight_count == 1
    change = comparison.changed_weights[0]
    assert change.path == "EAT.CELL_ENERGY"
    assert change.parent_value == 0.97
    assert change.child_value == 1.04
    assert change.delta == 1.04 - 0.97
    assert comparison.recorded_count_matches is True


def test_multiple_mutations_are_all_reported_and_count_disagreement_is_safe():
    comparison = compare_persisted_genomes(
        genome(),
        genome(eat_cell_energy=1.04, wait_bias=-0.5),
        recorded_mutated_weight_count=1,
    )

    assert {change.path for change in comparison.changed_weights} == {
        "EAT.CELL_ENERGY",
        "WAIT.BIAS",
    }
    assert comparison.changed_weight_count == 2
    assert comparison.recorded_count_matches is False


def test_founder_detail_and_parent_child_sibling_links_are_derived():
    founder = inspect_organism(family_rows(), 10)
    child = inspect_organism(family_rows(), 11)

    assert founder is not None
    assert founder.founder_organism_id == 10
    assert founder.generation == 0
    assert founder.genome_comparison is None
    assert founder.child_organism_ids == (11, 12)

    assert child is not None
    assert child.parent_organism_id == 10
    assert child.parent_exists is True
    assert child.parent_genome == genome()
    assert child.founder_organism_id == 10
    assert child.generation == 1
    assert child.sibling_organism_ids == (12,)
    assert child.child_organism_ids == (13,)
    assert child.genome_comparison is not None
    assert child.genome_comparison.changed_weight_count == 1


def test_non_weight_genome_difference_is_not_counted_as_a_mutated_weight():
    child = genome()
    child["reproduction_threshold"] = 151.0

    comparison = compare_persisted_genomes(
        genome(), child, recorded_mutated_weight_count=0
    )

    assert comparison.identical is False
    assert comparison.changed_weight_count == 0
    assert comparison.recorded_count_matches is True
    assert comparison.reproduction_threshold_difference is not None
    assert comparison.reproduction_threshold_difference.delta == 1.0


def test_missing_organism_returns_none():
    assert inspect_organism(family_rows(), 999) is None
