import json

import itertools
from dataclasses import dataclass, replace

class Error(Exception): pass
class Warning(Exception): pass

@dataclass
class HWSSettings:
    minConfirmations: int
    minWithdrawal: int

@dataclass
class Currency:
    symbol: str
    type: str
    hwsSettings: HWSSettings
    custodialPrecision: int

    def __post_init__(self):
        if self.hwsSettings:
            self.hwsSettings = HWSSettings(**self.hwsSettings)

    def __str__(self):
        return f"[{self.symbol}, {self.type}]"

    def check(self, ref):
        self.check_precision(ref)
        self.check_min_confirmations()

    def check_min_confirmations(self):
        if self.hwsSettings is None:
            return

        if (self.symbol == "ETH" or self.type == "ERC20") and \
            self.hwsSettings.minConfirmations != 30:
            raise Error(f"minConfirmations {self.hwsSettings.minConfirmations}, expected 30")

    def check_precision(self, ref):
        precision = self.custodialPrecision

        if self.symbol == "ETH":
            expected = 8
        elif self.type == "COIN":
            expected = min(ref.decimals, 9)
        elif self.type == "ERC20":
            expected = min(ref.decimals, 8)
        else:
            raise Error(f"Invalid type {self.type}")
        
        if precision != expected:
            raise Error(f"custodialPrecision {precision}, expected {expected}")


@dataclass
class Coin:
    symbol: str
    name: str
    decimals: int
    logo: str

    def __str__(self):
        return f"[{self.symbol}, COIN]"

    def check(self):
        if self.logo is None:
            raise Warning(f"No logo")


@dataclass
class ERC20Token:
    address: str
    decimals: int
    logo: str
    name: str
    symbol: str
    website: str

    def __str__(self):
        return f"[{self.symbol}, ERC20]"

    def check(self):
        if self.logo is None:
            raise Warning(f"No logo")



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
    coins = list(map(lambda x: Coin(**x), read_json("coins.json")))
    erc20_tokens = list(map(lambda x: ERC20Token(**x), read_json("erc20-tokens.json")))

    currencies = map(lambda x: Currency(**x), read_json("custody.json"))

    combined = sorted(itertools.chain(coins, erc20_tokens), key=lambda x: x.symbol)
    duplicates = find_duplicates(combined, lambda t: t.symbol)

    if duplicates:
        raise Exception(f"Duplicate elements found: {compress_duplicates(duplicates)}")

    coins = {x.symbol: x for x in coins}
    erc20_tokens = {x.symbol: x for x in erc20_tokens}

    for currency in currencies:
        try:
            if currency.type == "COIN":
                ref = coins.get(currency.symbol)
            else:
                ref = erc20_tokens.get(currency.symbol)

            if ref is None:
                raise Error("Reference not found")

            ref.check()
            currency.check(ref)

            log_success(f"{currency}: OK")
        except Warning as e:
            log_warning(f"{currency}: {e}")
        except Error as e:
            log_error(f"{currency}: {e}")


if __name__ == '__main__':
    main()
