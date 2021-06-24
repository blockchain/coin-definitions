import os
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
    removed: bool = False

@dataclass
class ERC20Token:
    address: str
    decimals: int
    logo: str
    name: str
    symbol: str
    website: str

@dataclass
class Blockchain:
    decimals: int
    description: str
    explorer: str
    name: str
    symbol: str
    type: str
    website: str
    status: str = None
    short_description: str = None
    source_code: str = None
    white_paper: str = None
    research: str = None
    socials: object = None
    tags: str = None

blockchains_denylist = [
    ('AVAX', 'Avalanche C-Chain'),
    ('AVAX', 'Avalanche X-Chain'),
    ('BCH', 'smartBCH'),
    ('BNB', 'Smart Chain')
]

def read_json(path):
    with open(path) as json_file:
        return json.load(json_file)

def find_duplicates(items, key):
    groups = itertools.groupby(sorted(items, key=key), key)
    groups = [(symbol, list(items)) for symbol, items in groups]
    return [(symbol, items) for symbol, items in groups if len(items) > 1]

def compress_duplicates(duplicates):
    return [(symbol, [x.name for x in group]) for symbol, group in duplicates]

def read_blockchains_list(blockchains_dir):
    for blockchain_dir in sorted(os.listdir(blockchains_dir)):
        blockchain_info_path = os.path.join(blockchains_dir, blockchain_dir, "info", "info.json")

        if not os.path.exists(blockchain_info_path):
            continue

        yield read_json(blockchain_info_path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("currencies", help="Path to currencies JSON file")
    parser.add_argument("fiat_currencies", help="Path to fiat currencies JSON file")
    parser.add_argument("blockchains_dir", help="Path to the blockchains directory")
    parser.add_argument("erc20_tokens", help="Path to erc20 tokens JSON file")
    args = parser.parse_args()

    currencies = map(lambda x: Currency(**x), read_json(args.currencies))
    fiat_currencies = map(lambda x: Currency(**x, type="FIAT"), read_json(args.fiat_currencies))
    erc20_tokens = map(lambda x: ERC20Token(**x), read_json(args.erc20_tokens))
    blockchains = map(lambda x: Blockchain(**x), 
                      filter(lambda x: x.get('symbol'), 
                             read_blockchains_list(args.blockchains_dir)))

    blockchains = [b for b in blockchains 
                   if (b.symbol, b.name) not in blockchains_denylist]

    duplicates = find_duplicates(blockchains, lambda t: t.symbol)

    if duplicates:
        print(f"Duplicate blockchains found: {compress_duplicates(duplicates)}")
        return

    currencies = list(currencies) + list(fiat_currencies)
    duplicates = find_duplicates(currencies, lambda t: t.symbol)

    if duplicates:
        print(f"Duplicate currencies found: {compress_duplicates(duplicates)}")
        return

    # erc20_tokens = list(erc20_tokens)
    # duplicates = find_duplicates(blockchains + erc20_tokens, lambda t: t.symbol)

    # if duplicates:
    #     print(f"Conflicting blockchains and tokens found: {compress_duplicates(duplicates)}")
    #     return

    blockchains_by_symbol = {x.symbol: x for x in blockchains if x.symbol}
    tokens_by_symbol = {x.symbol: x for x in erc20_tokens}

    for currency in currencies:
        token = tokens_by_symbol.get(currency.symbol)
        blockchain = blockchains_by_symbol.get(currency.symbol)

        ref = token or blockchain

        if ref:
            if currency.name == ref.name and currency.decimals == ref.decimals:
                print(f" - ✅ {currency.symbol}: OK")
                continue
            if currency.name != ref.name:
                print(f" - ❌ {currency.symbol}: Name mismatch: '{currency.name}' vs '{ref.name}'")
            if currency.decimals != ref.decimals:
                print(f" - ❌ {currency.symbol}: Decimals mismatch: {currency.decimals} vs {ref.decimals}")
        else:
            print(f" - ❓ {currency.symbol} ({currency.name}): Can't verify")


if __name__ == '__main__':
    main()
