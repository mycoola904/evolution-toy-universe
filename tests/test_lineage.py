from experiments.lineage import analyze_lineages


def row(
    organism_id,
    parent_id,
    birth_tick,
    death_tick,
    lifespan,
    mutated_weight_count,
    energy_consumed,
    distance_moved,
):
    return {
        "organism_id": organism_id,
        "parent_organism_id": parent_id,
        "birth_tick": birth_tick,
        "death_tick": death_tick,
        "lifespan": lifespan,
        "mutated_weight_count": mutated_weight_count,
        "energy_consumed": energy_consumed,
        "distance_moved": distance_moved,
    }


def family_rows():
    return [
        row(0, None, 0, 8, 8, None, 10.0, 1),
        row(1, 0, 2, 10, 8, 2, 5.0, 2),
        row(2, 1, 7, None, 3, 0, 1.0, 3),
        row(10, None, 0, 7, 7, None, 2.0, 0),
    ]


def test_family_detection_depth_counts_survival_and_mutation_aggregation():
    analysis = analyze_lineages(family_rows())

    assert [family.founder_organism_id for family in analysis.families] == [0, 10]
    family = analysis.families[0]
    assert family.total_family_members == 3
    assert family.total_descendants == 2
    assert family.generations_reached == 2
    assert family.alive_at_end == 1
    assert family.dead == 2
    assert family.reproducing_family_members == 2
    assert family.total_births_produced == 2
    assert family.longest_lived_organism_id == 0
    assert family.longest_lifespan == 8
    assert family.total_energy_consumed == 16.0
    assert family.average_energy_consumed == 16.0 / 3
    assert family.total_distance_moved == 6
    assert family.average_distance_moved == 2.0
    assert family.organisms_that_received_mutation == 1
    assert family.total_mutated_weights == 2
    assert family.extinction_tick is None
    assert family.lineage_survived is True

    extinct = analysis.families[1]
    assert extinct.extinction_tick == 7
    assert extinct.lineage_survived is False


def test_family_tree_reconstructs_children_and_generations():
    tree = analyze_lineages(family_rows()).trees_by_founder[0]

    assert tree.organism_id == 0
    assert tree.generation == 0
    assert tree.child_count == 1
    child = tree.children[0]
    assert child.organism_id == 1
    assert child.generation == 1
    assert child.received_mutation is True
    assert child.child_count == 1
    grandchild = child.children[0]
    assert grandchild.organism_id == 2
    assert grandchild.generation == 2
    assert grandchild.received_mutation is False
