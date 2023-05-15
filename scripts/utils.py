import glob
import json
import sys


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def map_chunked(f, items, chunk_size):
    progress = 0
    for chunk in chunks(items, chunk_size):
        yield f(chunk)
        progress += len(chunk)
        sys.stdout.write(f"...{int(progress / len(items) * 100)}%")
        sys.stdout.flush()
    sys.stdout.write("\n")


def read_json(path):
    with open(path) as json_file:
        return json.load(json_file)


def multiread_json(base_dir, pattern):
    for target in sorted(glob.glob(base_dir + pattern)):
        key = target.replace(base_dir, '').partition("/")[0]
        yield key, read_json(target)