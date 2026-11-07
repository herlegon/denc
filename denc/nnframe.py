from dataclasses import dataclass
import numpy as np
import torch
from torch import Tensor



@dataclass(slots=True)
class NnFrame:
    f_no: int = 0
    tensor: Tensor | np.ndarray = None
    channel_last: bool = False

    # last flag is used by temporal models
    last: bool = False

    # specific to cuda
    event: torch.cuda.Event = None


def mark_frame_ready(frame: NnFrame, stream: torch.cuda.Stream):
    event = torch.cuda.Event()
    event.record(stream)
    frame.event = event


def wait_frame_ready(frame: NnFrame, stream: torch.cuda.Stream):
    stream.wait_event(frame.event)
    frame.tensor.record_stream(stream)
