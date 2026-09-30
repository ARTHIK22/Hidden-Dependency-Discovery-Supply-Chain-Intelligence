MAX_WORKFLOW_STEPS = 9


def should_stop(*, sequence: int, max_steps: int = MAX_WORKFLOW_STEPS, failed: bool = False) -> bool:
    return failed or sequence >= max_steps
