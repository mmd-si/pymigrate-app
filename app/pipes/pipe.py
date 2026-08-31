"""A small synchronous fluent wrapper for composing transformation stages.

Ported from ``pymigrate/migrate-worker/app/pipes/pipe.py`` (+ ``ref.py``). Only
the CPU-bound normalize/validate portion runs through this; the Odoo-touching
``Mapper.map`` stage is async and is awaited directly by the drain, not chained
here.
"""

from typing import Any, Callable, Optional

from app.pipes.errors import PipelineError


class Ref[T]:
    """A mutable single-slot box, used to capture an intermediate value out of
    a pipeline so error handlers can reference it (e.g. the normalized barcode).
    """

    __value: T
    __set: bool = False

    def set(self, value: T) -> None:
        self.__value = value
        self.__set = True

    def is_set(self) -> bool:
        return self.__set

    def value(self) -> T:
        return self.__value


class Pipe[T]:
    __value: T

    def __init__(self, value: T):
        self.__value = value

    @classmethod
    def of[U](cls, value: U) -> 'Pipe[U]':
        return Pipe(value)

    def tap(self, ref: Ref) -> 'Pipe[T]':
        ref.set(self.__value)
        return self

    def guard(
        self,
        method: Callable[[T], bool],
        error_fn: Optional[Callable[[T], Exception]] = None,
    ) -> 'Pipe[T]':
        try:
            ok = method(self.__value)
        except Exception as e:
            raise PipelineError(
                f"Error occurred in pipeline calling guard '{method.__name__}'."
            ) from e
        if not ok:
            raise (
                error_fn(self.__value)
                if error_fn
                else PipelineError(f"Guard '{method.__name__}' failed.")
            )
        return self

    def pipe[U](self, method: Callable[[T], U]) -> 'Pipe[U]':
        try:
            return Pipe(method(self.__value))
        except Exception as e:
            raise PipelineError(
                f"Error occurred in pipeline calling filter '{method.__name__}'."
            ) from e

    def consume[U](self, method: Callable[[T], U]) -> U:
        try:
            return method(self.__value)
        except Exception as e:
            raise PipelineError(
                f"Error occurred in pipeline calling consumer '{method.__name__}'."
            ) from e

    def peek(self) -> T:
        return self.__value
