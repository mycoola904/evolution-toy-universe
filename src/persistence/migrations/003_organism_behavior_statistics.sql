ALTER TABLE organism_results
    ADD COLUMN wait_count BIGINT,
    ADD COLUMN eat_attempt_count BIGINT,
    ADD COLUMN successful_eat_count BIGINT,
    ADD COLUMN unsuccessful_eat_count BIGINT,
    ADD COLUMN move_forward_count BIGINT,
    ADD COLUMN turn_left_count BIGINT,
    ADD COLUMN turn_right_count BIGINT,
    ADD COLUMN final_action TEXT,
    ADD CONSTRAINT organism_behavior_complete_or_legacy CHECK (
        num_nonnulls(
            wait_count,
            eat_attempt_count,
            successful_eat_count,
            unsuccessful_eat_count,
            move_forward_count,
            turn_left_count,
            turn_right_count
        ) IN (0, 7)
        AND (wait_count IS NOT NULL OR final_action IS NULL)
    ),
    ADD CONSTRAINT organism_behavior_counts_nonnegative CHECK (
        wait_count >= 0
        AND eat_attempt_count >= 0
        AND successful_eat_count >= 0
        AND unsuccessful_eat_count >= 0
        AND move_forward_count >= 0
        AND turn_left_count >= 0
        AND turn_right_count >= 0
    ),
    ADD CONSTRAINT organism_eat_counts_consistent CHECK (
        successful_eat_count + unsuccessful_eat_count = eat_attempt_count
    ),
    ADD CONSTRAINT organism_movement_count_consistent CHECK (
        move_forward_count = distance_moved
    ),
    ADD CONSTRAINT organism_action_total_consistent CHECK (
        wait_count
        + eat_attempt_count
        + move_forward_count
        + turn_left_count
        + turn_right_count = lifespan
    ),
    ADD CONSTRAINT organism_final_action_known CHECK (
        final_action IS NULL
        OR final_action IN (
            'WAIT',
            'EAT',
            'MOVE_FORWARD',
            'TURN_LEFT',
            'TURN_RIGHT'
        )
    ),
    ADD CONSTRAINT organism_final_action_consistent CHECK (
        (
            COALESCE(
                wait_count
                + eat_attempt_count
                + move_forward_count
                + turn_left_count
                + turn_right_count,
                0
            ) = 0
            AND final_action IS NULL
        )
        OR (
            wait_count
            + eat_attempt_count
            + move_forward_count
            + turn_left_count
            + turn_right_count > 0
            AND final_action IS NOT NULL
        )
    );
