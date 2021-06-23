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
class FiatCurrency:
    symbol: str
    name: str
    decimals: int

def read_json(path):
    with open(path) as json_file:
        return json.load(json_file)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("currencies", help="Path to currencies JSON file")
    parser.add_argument("fiat_currencies", help="Path to fiat currencies JSON file")
    parser.add_argument("erc20_tokens", help="Path to erc20 tokens JSON file")
    args = parser.parse_args()

    currencies = map(lambda x: Currency(**x), read_json(args.currencies))
    fiat_currencies = map(lambda x: FiatCurrency(**x), read_json(args.fiat_currencies))
    erc20_tokens = map(lambda x: ERC20Token(**x), read_json(args.erc20_tokens))

    tokens_by_symbol = {x.symbol: x for x in erc20_tokens}

    for currency in itertools.chain(currencies, fiat_currencies):
        token = tokens_by_symbol.get(currency.symbol)

        if not token:
            continue

        if currency.name != token.name:
            print(f"Name mismatch for {currency.symbol}: '{currency.name}' vs '{token.name}'")

        if currency.decimals != token.decimals:
            print(f"Decimals mismatch for {currency.symbol}: {currency.decimals} vs {token.decimals}")


if __name__ == '__main__':
    main()
