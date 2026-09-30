from pathlib import Path
import sys
import time
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Evaluate the loading time because of torch which is slow to be loaded
# (~1.3s)

start_time: float = time.time()
import denc
# from denc import MediaStream
print(f"loaded in {(time.time() - start_time) * 1000.} ms")
