import experiments.lineage_mutations as lineage_mutations
from experiments.lineage_mutations import build_lineage_mutation_explorer


def genome(a=0.0, b=0.0):
    return {
        "reproduction_threshold": 100.0,
        "weights": {"TURN_RIGHT": {"A": a, "B": b}},
    }


def row(
    organism_id,
    parent_id,
    birth_tick,
    persisted_genome,
    mutated_count,
    death_tick=None,
):
    return {
        "organism_id": organism_id,
        "parent_organism_id": parent_id,
        "birth_tick": birth_tick,
        "death_tick": death_tick,
        "mutated_weight_count": mutated_count,
        "genome": persisted_genome,
    }


def lineage_rows():
    return [
        row(10, None, 0, genome(), None, death_tick=9),
        row(11, 10, 1, genome(a=0.1, b=0.2), 2, death_tick=8),
        row(12, 11, 2, genome(a=0.1, b=0.2), 0, death_tick=7),
        row(13, 12, 3, genome(a=0.3, b=0.2), 1),
        # A later carrier proves selection is by first observation, not caller.
        row(19, 13, 5, genome(a=0.3, b=0.2), 0),
    ]


def test_path_reaches_founder_and_selects_earliest_exact_genome_carrier():
    explorer = build_lineage_mutation_explorer(
        lineage_rows(),
        founder_organism_id=10,
        selected_genome_organism_id=19,
    )

    assert explorer is not None
    assert explorer.ancestry_complete is True
    assert explorer.representative_organism_id == 13
    assert explorer.representative_generation == 3
    assert explorer.representative_birth_tick == 3
    assert [node.organism_id for node in explorer.path] == [10, 11, 12, 13]


def test_multiple_and_repeated_mutations_remain_chronological():
    explorer = build_lineage_mutation_explorer(
        lineage_rows(),
        founder_organism_id=10,
        selected_genome_organism_id=13,
    )

    assert explorer is not None
    first_event = explorer.path[1]
    second_event = explorer.path[3]
    assert [change.path for change in first_event.changes] == [
        "TURN_RIGHT.A",
        "TURN_RIGHT.B",
    ]
    assert [change.path for change in second_event.changes] == ["TURN_RIGHT.A"]
    assert explorer.path[2].has_mutation is False
    assert [step.node.organism_id for step in explorer.mutation_only_steps] == [
        10,
        11,
        13,
    ]
    assert explorer.mutation_only_steps[-1].skipped_unchanged_generations == 1
    assert explorer.total_mutation_events == 2
    assert explorer.total_weight_changes == 3
    assert explorer.unique_weights_changed == 2


def test_cumulative_changes_include_net_delta_and_repeat_count():
    explorer = build_lineage_mutation_explorer(
        lineage_rows(),
        founder_organism_id=10,
        selected_genome_organism_id=13,
    )

    assert explorer is not None
    changes = {change.path: change for change in explorer.cumulative_differences}
    assert changes["TURN_RIGHT.A"].founder_value == 0.0
    assert changes["TURN_RIGHT.A"].selected_value == 0.3
    assert changes["TURN_RIGHT.A"].net_delta == 0.3
    assert changes["TURN_RIGHT.A"].mutation_count == 2
    assert changes["TURN_RIGHT.B"].mutation_count == 1


def test_branch_context_is_aggregated_from_persisted_descendants():
    explorer = build_lineage_mutation_explorer(
        lineage_rows(),
        founder_organism_id=10,
        selected_genome_organism_id=13,
    )

    assert explorer is not None
    branch = explorer.path[1].branch
    assert branch.direct_children == 1
    assert branch.total_known_descendants == 3
    assert branch.surviving_descendants == 2
    assert branch.deepest_descendant_generation == 4
    assert branch.descendants_include_selected_genome is True


def test_display_digest_is_not_used_as_genome_identity(monkeypatch):
    rows = [
        row(1, None, 0, genome(), None),
        row(2, 1, 1, genome(a=0.1), 1),
        row(3, 1, 1, genome(b=0.1), 1),
    ]
    monkeypatch.setattr(
        lineage_mutations,
        "genome_display_digest",
        lambda _genome: "same-digest",
    )

    explorer = build_lineage_mutation_explorer(
        rows,
        founder_organism_id=1,
        selected_genome_organism_id=3,
    )

    assert explorer is not None
    assert explorer.selected_genome_digest == "same-digest"
    assert explorer.representative_organism_id == 3
    assert explorer.cumulative_differences[0].path == "TURN_RIGHT.B"


def test_founder_genome_and_direct_mutation_are_handled():
    rows = [
        row(1, None, 0, genome(), None),
        row(2, 1, 1, genome(), 0),
        row(3, 1, 2, genome(a=0.2), 1),
    ]

    identical = build_lineage_mutation_explorer(
        rows,
        founder_organism_id=1,
        selected_genome_organism_id=2,
    )
    direct = build_lineage_mutation_explorer(
        rows,
        founder_organism_id=1,
        selected_genome_organism_id=3,
    )

    assert identical is not None
    assert identical.representative_organism_id == 1
    assert identical.total_mutation_events == 0
    assert identical.cumulative_differences == ()
    assert direct is not None
    assert [node.organism_id for node in direct.path] == [1, 3]
    assert direct.total_mutation_events == 1


def test_missing_ancestry_returns_known_path_with_warning():
    rows = [row(7, 99, 5, genome(a=0.2), 1)]

    explorer = build_lineage_mutation_explorer(
        rows,
        founder_organism_id=1,
        selected_genome_organism_id=7,
    )

    assert explorer is not None
    assert explorer.ancestry_complete is False
    assert explorer.representative_generation is None
    assert [node.organism_id for node in explorer.path] == [7]
    assert "Parent organism 99 is unavailable" in explorer.ancestry_warning
