from collections.abc import Callable, Iterable


def run_sequential(tasks: Iterable[tuple[str, Callable[[], dict]]]) -> list[dict]:
    """Run bounded local tasks in declared order and stop on first failure."""
    results = []
    for stage, task in tasks:
        try:
            results.append({"stage": stage, "status": "completed", "output": task()})
        except Exception as exc:
            results.append({"stage": stage, "status": "failed", "error": str(exc)})
            break
    return results
