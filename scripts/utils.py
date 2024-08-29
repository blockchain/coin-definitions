import glob
import json
import sys
from typing import List, Any, Dict, Tuple, TypeVar, Callable, Generator

T = TypeVar('T')
R = TypeVar('R')

def chunks(lst: List[T], n: int) -> Generator[List[T], None, None]:
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def map_chunked(f: Callable[[List[T]], R], items: List[T], chunk_size: int) -> Generator[R, None, None]:
    progress = 0
    for chunk in chunks(items, chunk_size):
        yield f(chunk)
        progress += len(chunk)
        sys.stdout.write(f"...{int(progress / len(items) * 100)}%")
        sys.stdout.flush()
    sys.stdout.write("\n")

def read_json(path: str) -> Dict[str, Any]:
    with open(path) as json_file:
        return json.load(json_file)

def multiread_json(base_dir: str, pattern: str) -> Generator[Tuple[str, Dict[str, Any]], None, None]:
    for target in sorted(glob.glob(base_dir + pattern)):
        key = target.replace(base_dir, '').partition("/")[0]
        yield key, read_json(target)
