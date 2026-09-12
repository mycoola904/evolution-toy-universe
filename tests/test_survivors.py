from experiments.survivors import build_survivor_explorer


GENOME_A = {"weights": {"EAT": {"CELL_ENERGY": 1.0}}}
GENOME_B = {"weights": {"EAT": {"CELL_ENERGY": 1.1}}}
GENOME_C = {"weights": {"WAIT": {"BIAS": 0.2}}}


def row(
    organism_id,
    parent_id,
    birth_tick,
    death_tick,
    lifespan,
    final_energy,
    genome,
):
    return {
        "organism_id": organism_id,
        "parent_organism_id": parent_id,
        "birth_tick": birth_tick,
        "death_tick": death_tick,
        "lifespan": lifespan,
        "final_energy": final_energy,
        "genome": genome,
    }


def survivor_rows():
    return [
        # Founder 1 has five historical descendants, but only two survive.
        row(1, None, 0, 9, 9, 0, GENOME_A),
        row(2, 1, 1, 4, 3, 0, GENOME_A),
        row(3, 1, 2, None, 8, 43, GENOME_A),
        row(4, 2, 3, 6, 3, 0, GENOME_B),
        row(5, 2, 4, None, 6, 21, GENOME_B),
        row(6, 3, 5, 7, 2, 0, GENOME_A),
        # Founder 10 has one surviving descendant and sorts second.
        row(10, None, 0, 5, 5, 0, GENOME_C),
        row(11, 10, 1, None, 7, 30, GENOME_C),
    ]


def test_survivors_are_grouped_counted_and_sorted_by_founder_and_genome():
    explorer = build_survivor_explorer(survivor_rows())

    assert [group.founder_organism_id for group in explorer.founders] == [1, 10]
    founder = explorer.founders[0]
    assert founder.survivor_count == 2
    assert founder.surviving_descendant_count == 2
    assert founder.total_descendants == 5
    assert founder.descendant_survivor_percentage == 40.0
    assert founder.distinct_survivor_genomes == 2
    assert founder.average_age == 7.0
    assert founder.oldest_age == 8
    assert founder.average_children == 0.5
    assert founder.maximum_children == 1
    assert founder.latest_generation == 2
    assert [group.survivor_count for group in founder.genomes] == [1, 1]
    assert [
        survivor.organism_id
        for group in founder.genomes
        for survivor in group.survivors
    ] == [3, 5]
    assert all(
        survivor.organism_id not in {1, 2, 4, 6}
        for group in founder.genomes
        for survivor in group.survivors
    )


def test_same_founder_keeps_distinct_persisted_genomes_separate():
    founder = build_survivor_explorer(survivor_rows()).founders[0]

    assert len(founder.genomes) == 2
    assert founder.genomes[0].genome_id != founder.genomes[1].genome_id
    historical_counts = sorted(
        group.historical_organism_count for group in founder.genomes
    )
    assert historical_counts == [2, 4]
    genome_a = next(group for group in founder.genomes if group.historical_organism_count == 4)
    assert genome_a.representative_organism_id == 1


def test_genomes_and_organisms_use_success_oriented_stable_ordering():
    rows = [
        row(20, None, 0, 2, 2, 0, GENOME_A),
        row(21, 20, 1, None, 4, 10, GENOME_B),
        row(22, 20, 1, None, 7, 10, GENOME_A),
        row(23, 20, 2, None, 7, 10, GENOME_A),
    ]

    founder = build_survivor_explorer(rows).founders[0]

    assert [group.survivor_count for group in founder.genomes] == [2, 1]
    assert [item.organism_id for item in founder.genomes[0].survivors] == [22, 23]
    assert founder.genomes[0].average_age == 7.0


def test_zero_survivors_returns_an_empty_explorer():
    rows = [row(1, None, 0, 3, 3, 0, GENOME_A)]

    explorer = build_survivor_explorer(rows)

    assert explorer.founders == ()
    assert explorer.survivor_count == 0
