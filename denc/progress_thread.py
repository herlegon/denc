from queue import Queue
from threading import Event
import time
from rich.progress import (
    BarColumn,
    Progress,
    TimeRemainingColumn,
    TimeElapsedColumn,
)

from denc.base_thread import BaseThread


class ProgressThread(BaseThread):
    def __init__(
        self,
        total: int = 0,
        refresh_rate: int = 2,
        description: str = "[green]Processing...",
    ) -> None:
        super().__init__()
        self.description = description
        self._stop_event = Event()
        self._stop_event.clear()
        self.in_queue: Queue = Queue()
        self.total: int = total
        self._encoded: int = 0
        self.interval: float = 1. / refresh_rate
        self.refresh_rate: int = refresh_rate
        self.is_running: bool = False
        self.previous_timestamp: float = 0.
        self.start_time: float = 0.
        self.previous_encoded = 0
        self._elapsed: float = 0.
        self.encoding_start_time: float = 0.
        self.encoded: int = 0


    def run(self):
        self.is_running = True

        in_queue: Queue = self.in_queue
        in_queue.put((0, 0))
        progress = Progress(
            BarColumn(bar_width=40),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "frame:",
            "{task.fields[encoded]}" + f"/{self.total}",
            "elapsed=",
            TimeElapsedColumn(),
            "fps=",
            "{task.fields[fps]:<3.2f}",
            "ETA",
            TimeRemainingColumn(),
            refresh_per_second=self.refresh_rate,
        )
        progress.start()
        self.task_id = progress.add_task(
            self.description,
            total=self.total,
            encoded=0,
            fps=0,
            start=True
        )

        previous_encoded = 0
        previous_encoded = 0
        self.start_time = time.perf_counter()
        self.previous_timestamp = self.start_time
        self.encoding_start_time = self.start_time

        with progress:
            while not self._stop_event.is_set():
                data = in_queue.get(block=True)
                if data is None:
                    break
                encoded, elapsed = data
                progress.update(
                    self.task_id,
                    advance=encoded - previous_encoded,
                    encoded=encoded,
                    fps=float(encoded) / elapsed if elapsed else 0,
                )
                previous_encoded = encoded

                # if elapsed:
                #     fps = encoded / elapsed
                #     print(
                #         " ".join((
                #         purple(f"{(100 * encoded)/self.total:0.1f}%"),
                #         f"frame: {encoded}/{self.total}",
                #         f"elapsed=", yellow(f"{int(elapsed)}"),
                #         f"fps= {fps:.1f}",
                #         blue(f"ETA {int(fps * encoded)}"),
                #         '\r')),
                #         # end='\r',
                #         file=sys.stdout,
                #         flush = True
                #     )

                if self._stop_event.is_set():
                    break

        time.sleep(0.1)
        self.is_running = False


    def stop(self, force: bool=False) -> None:
        if force:
            while not self.in_queue.empty():
                try:
                    self.in_queue.get_nowait()
                except Exception:
                    break
        self.in_queue.put_nowait(None)
        self._stop_event.set()


    def put(self, delta: int | None, force: bool = False):
        now = time.perf_counter()
        if delta is None:
            self._elapsed = now - (self.encoding_start_time or now)
            self.in_queue.put_nowait((self.encoded, self._elapsed))
            self.in_queue.put_nowait(None)
            return

        if self.encoding_start_time == 0:
            self.encoding_start_time = now

        self.encoded += delta

        if (now - self.previous_timestamp) >= self.interval or force:
            self.previous_timestamp = now
            self.in_queue.put_nowait((self.encoded, now - self.start_time))


    def elapsed(self) -> float:
        return self._elapsed
