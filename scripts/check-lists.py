import json
import argparse

import itertools
from dataclasses import dataclass

@dataclass
class Currency:
    symbol: str
    name: str
    type: str
    decimals: int
    logo: str = None
    removed: bool = False


def read_json(path):
    with open(path) as json_file:
        return json.load(json_file)

def find_duplicates(items, key):
    groups = itertools.groupby(sorted(items, key=key), key)
    groups = [(symbol, list(items)) for symbol, items in groups]
    return [(symbol, items) for symbol, items in groups if len(items) > 1]

def compress_duplicates(duplicates):
    return [(symbol, [x.name for x in group]) for symbol, group in duplicates]

def log_success(msg): 
    print(" ✅ " + msg)

def log_warning(msg): 
    print(" ⚠️  " + msg)

def log_error(msg): 
    print(" 🛑 " + msg)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("currencies", help="Path to currencies JSON file")
    args = parser.parse_args()

    currencies = list(map(lambda x: Currency(**x), read_json(args.currencies)))

    duplicates = find_duplicates(currencies, lambda t: t.symbol)

    if duplicates:
        print(f"Duplicate blockchains found: {compress_duplicates(duplicates)}")
        return

    for currency in currencies:
        if currency.logo is None:
            log_error(f"{currency.symbol}: No logo")
        else:
            log_success(f"{currency.symbol}: OK")


if __name__ == '__main__':
    main()
