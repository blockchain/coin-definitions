import json
import argparse

import itertools
from dataclasses import dataclass, replace

class Error(Exception): pass
class Warning(Exception): pass

@dataclass
class CustodialSettings:
    minConfirmations: int
    minWithdrawal: int
    custodialPrecision: int

@dataclass
class Currency:
    symbol: str
    name: str
    type: str
    decimals: int
    settings: CustodialSettings
    logo: str

    def __post_init__(self):
        if self.settings:
            self.settings = CustodialSettings(**self.settings)

    def __str__(self):
        return f"[{self.symbol}, {self.type}]"

    def check(self):
        if self.logo is None:
            raise Warning(f"No logo")
        
        if self.type != 'COIN':
            raise Error(f"Invalid type '{self.type}'")
        
        if self.settings is None:
            raise Warning(f"No custodial settings")
        
        check_custodial_precision(self)

@dataclass
class ERC20Token:
    address: str
    decimals: int
    logo: str
    name: str
    settings: CustodialSettings
    symbol: str
    website: str

    def __post_init__(self):
        if self.settings:
            self.settings = CustodialSettings(**self.settings)

    def __str__(self):
        return f"[{self.symbol}, ERC20]"

    def check(self):
        if self.logo is None:
            raise Warning(f"No logo")
        
        if self.settings is not None:
            check_custodial_precision(self)


def check_custodial_precision(item):
    precision = item.settings.custodialPrecision
    expected = min(item.decimals, 9)
        
    if precision != expected:
        raise Error(f"custodialPrecision {precision}, expected {expected}")


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
    parser.add_argument("erc20_tokens", help="Path to erc20 tokens JSON file")
    args = parser.parse_args()

    currencies = map(lambda x: Currency(**x), read_json(args.currencies))
    erc20_tokens = map(lambda x: ERC20Token(**x), read_json(args.erc20_tokens))

    items = list(itertools.chain(currencies, erc20_tokens))

    duplicates = find_duplicates(items, lambda t: t.symbol)

    if duplicates:
        raise Exception(f"Duplicate currencies found: {compress_duplicates(duplicates)}")

    for item in items:
        try:
            item.check()
        except Warning as e:
            log_warning(f"{item}: {e}")
        except Error as e:
            log_error(f"{item}: {e}")


if __name__ == '__main__':
    main()
