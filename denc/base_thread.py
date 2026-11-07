from __future__ import annotations
import abc
from collections.abc import Callable
import queue
from queue import Full, Queue
from threading import Event, Thread
from typing import TYPE_CHECKING, Any, Iterable, Mapping, Optional, Type
import numpy as np
import torch

from .nnframe import NnFrame
if TYPE_CHECKING:
    from .progress_thread import ProgressThread


DEC_ENC_HOST_NBUFFERS = 1


class BaseThread(abc.ABC, Thread):
    def __init__(self,
        group: None = None,
        target: Callable[..., object] | None = None,
        name: str | None = None,
        verbose: bool = False,
        args: Iterable[Any] = ...,
        kwargs: Mapping[str, Any] | None = None,
        *,
        daemon: bool | None = None
    ) -> None:
        super().__init__(group, target, name, args, kwargs, daemon=daemon)
        self._has_error: bool = False
        self._error_msg: str = ''
        self._verbose: bool = verbose

        self.producer: Optional[BaseThread] = None
        self.consumer: Optional[BaseThread] = None
        self._processing: bool = True
        self._is_cuda_workflow: bool = False

        self._stop_event = Event()
        self._stop_event.clear()
        self.in_queue: Queue = Queue(1)
        self.prescale: tuple[int, int, int] | None = None
        self.infer_stream: torch.cuda.Stream = None


    @property
    def verbose(self) -> bool:
        return self._verbose


    @verbose.setter
    def verbose(self, enabled: bool) -> None:
        self._verbose = enabled


    def error_encountered(self) -> tuple[bool, str]:
        return (self._has_error, self._error_msg)


    def stop(self, force: bool=False) -> None:
        self._stop_event.set()
        if force:
            while not self.in_queue.empty():
                self.in_queue.get_nowait()
        try:
            self.in_queue.put_nowait(None)
        except Full:
            pass
        self.put_frame(None)


    def ended(self) -> bool:
        return self.in_queue.empty()

    def set_producer(self, producer: Type[BaseThread]) -> None:
        self.producer = producer


    def set_consumer(self, consumer: Type[BaseThread]) -> None:
        self.consumer = consumer


    # @abc.abstractmethod
    def set_produce_flag(self) -> None:
        pass


    def put_tensor(self, frame: np.ndarray | torch.Tensor) -> bool:
        return False


    def put(self, data: Any, force: bool=False) -> None:
        pass


    def put_frame(self, frame: NnFrame) -> bool:
        try:
            self.in_queue.put(frame)
            return True
        except queue.Full:
            print("[V][I] no place")
            pass
        return False


    def set_progress_thread(self, progress_thread: ProgressThread) -> None:
        self.progress_thread = progress_thread


    def processing(self) -> bool:
        return self._processing


    @property
    def is_cuda_workflow(self) -> bool:
        return self._is_cuda_workflow


    @is_cuda_workflow.setter
    def is_cuda_workflow(self, enabled: bool) -> None:
        self._is_cuda_workflow = enabled and torch.cuda.is_available()
