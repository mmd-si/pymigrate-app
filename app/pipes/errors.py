class PipelineError(Exception):
    """Any failure raised while running a pipeline stage."""


class ValidationError(Exception):
    """A ``JoinedItem`` failed one or more validation rules."""


class GuardError(Exception):
    """A guard predicate says this item should be skipped (treated as done)."""
