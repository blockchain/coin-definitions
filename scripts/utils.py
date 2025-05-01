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

def decode_cardano_fingerprint(fingerprint, symbol):
    policy_id_mappings = {
        "asset1fc7e54kds62yggplh0vs65vcgrmn5n577per23" : "986f0548a2fd9758bc2a38d698041debe89568749e20ab9b75a7f4b7",
        "asset1l58ned7zvj57pxyp94kkqqyxvjelvtpcjjh743" : "986f0548a2fd9758bc2a38d698041debe89568749e20ab9b75a7f4b7",
        "asset1wrng86n9sz6t5d0lemvudur4ul6mgduv0gzuj8": "afc910d7a306d20c12903979d4935ae4307241d03245743548e76783",
        "asset1zvn33mj5kzgxtct7jr5qjyefu9ewk22xp0s0yw": "6ac8ef33b510ec004fe11585f7c5a9f0c07f0c23428ab4f29c1d7d10",
        "asset108xu02ckwrfc8qs9d97mgyh4kn8gdu9w8f5sxk": "279c909f348e533da5808898f87f9a14bb2c3dfbbacccd631d927a3f"
    }

    asset_name_hex = None
    if symbol:
        asset_name_hex = symbol.encode("utf-8").hex()

    if fingerprint in policy_id_mappings:
        return (policy_id_mappings[fingerprint], asset_name_hex)