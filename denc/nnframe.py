from dataclasses import dataclass
import numpy as np
from torch import Tensor



@dataclass(slots=True)
class NnFrame:
    f_no: int = 0
    tensor: Tensor | np.ndarray = None
    channel_last: bool = False

    # last flag is used by temporal models
    last: bool = False

