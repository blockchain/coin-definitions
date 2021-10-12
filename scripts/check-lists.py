import glob
import json

import itertools
import operator
from dataclasses import dataclass
from functools import reduce

class CheckResult:
    def __init__(self, ref, msg):
        self.ref = ref
        self.msg = msg

    def is_blocker(self):
        return self.BLOCKER

    def __str__(self):
        return f"{self.PREFIX} {self.ref}: {self.msg}"


class Error(CheckResult):
    PREFIX = " 🛑 "
    BLOCKER = True

class Warning(CheckResult):
    PREFIX = " ⚠️ "
    BLOCKER = False


@dataclass
class HWSSettings:
    minConfirmations: int
    minWithdrawal: int

@dataclass
class NabuSettings:
    custodialPrecision: int

@dataclass
class Currency:
    symbol: str
    displaySymbol: str
    type: str
    chain: str
    nabuSettings: NabuSettings
    hwsSettings: HWSSettings
    removed: bool = False

    def __post_init__(self):
        self.nabuSettings = NabuSettings(**self.nabuSettings)

        if self.hwsSettings:
            self.hwsSettings = HWSSettings(**self.hwsSettings)

    def __str__(self):
        chain = f":{self.chain}" if self.chain else ""
        return f"[{self.symbol}, {self.type}{chain}]"

    def check(self, ref, prices):
        yield from self.check_symbol()
        yield from self.check_type()
        yield from self.check_precision(ref)
        yield from self.check_min_confirmations()
        yield from self.check_price(ref, prices)

    def check_symbol(self):
        if self.symbol != self.displaySymbol:
            yield Warning(self, f"displayed as: {self.displaySymbol}")

    def check_type(self):
        if self.type not in ("COIN", "ERC20"):
            yield Error(self, f"Invalid type {self.type}")

    def check_price(self, ref, prices):
        if self.hwsSettings is None:
            return

        minWithdrawal = self.hwsSettings.minWithdrawal

        if minWithdrawal == 0:
            return

        try:
            price = ref.get_price(prices)
        except Exception as e:
            yield Warning(self, f"No price: {e}")
            return

        minWithdrawalValue = minWithdrawal * 1.0 / (10**ref.decimals) * price

        if not (0.01 < minWithdrawalValue < 10):
            yield Warning(self, f"minWithdrawal {minWithdrawal} -> "
                                f"${minWithdrawalValue:.3f} not in the $0.01-$10 USD range")

    def check_min_confirmations(self):
        if self.hwsSettings is None:
            return

        if (self.symbol == "ETH" or self.type == "ERC20") and \
            self.hwsSettings.minConfirmations != 30:
            yield Error(self, f"minConfirmations {self.hwsSettings.minConfirmations}, expected 30")

    def check_precision(self, ref):
        precision = self.nabuSettings.custodialPrecision

        if self.symbol == "ETH":
            expected = [8]
        elif ref.decimals < 9:
            expected = [ref.decimals]
        else:
            expected = [8, 9]
        
        if precision not in expected:
            yield Error(self, f"custodialPrecision {precision}, expected {expected}")


@dataclass
class Coin:
    symbol: str
    name: str
    key: str
    decimals: int
    logo: str

    def __str__(self):
        return f"[{self.symbol}, COIN]"

    def get_price(self, prices):
        return prices['coins']['prices'][self.symbol]

    def check(self):
        if self.logo is None:
            yield Warning(self, f"No logo")


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

    def get_price(self, prices):
        return prices['erc20_tokens']['prices'][self.address.lower()]["usd"]

    def check(self):
        if self.logo is None:
            yield Warning(self, f"No logo")


def read_json(path):
    with open(path) as json_file:
        return json.load(json_file)

def multiread_json(base_dir, pattern):
    for target in sorted(glob.glob(base_dir + pattern)):
        key = target.replace(base_dir, '').partition("/")[0]
        yield (key, read_json(target))

def find_duplicates(items, key):
    groups = itertools.groupby(sorted(items, key=key), key)
    groups = [(symbol, list(items)) for symbol, items in groups]
    return [(symbol, items) for symbol, items in groups if len(items) > 1]

def compress_duplicates(duplicates):
    return [(symbol, [x.name for x in group]) for symbol, group in duplicates]

def check_currencies(currencies, coins, erc20_tokens, chains, prices):
    coins = {x.symbol: x for x in coins}
    erc20_tokens = {x.symbol: x for x in erc20_tokens}
    chains = {k: {t.symbol: t for t in v} for k, v in chains.items()}

    for currency in currencies:
        if currency.symbol.upper() != currency.symbol:
            yield Error(currency, f"Contains mix of lower and upper case letters")

        if currency.type == "COIN":
            ref = coins.get(currency.symbol)
        elif currency.type == "ERC20":
            if currency.chain == "ethereum":
                ref = erc20_tokens.get(currency.symbol)
            else:
                ret = chains.get(currency.chain).get(currency.symbol)
        else:
            yield Error(currency, "Invalid type")
            continue

        if ref is None:
            yield Error(currency, "Reference not found")
            continue

        yield from itertools.chain(ref.check(), currency.check(ref, prices))


ETH_EXT_ASSETS_PRICES = "extensions/blockchains/ethereum/assets/prices.json"
EXT_BLOCKCHAINS_PRICES = "extensions/blockchains/prices.json"


def main():
    coins = list(map(lambda x: Coin(**x), read_json("coins.json")))
    erc20_tokens = list(map(lambda x: ERC20Token(**x), read_json("erc20-tokens.json")))
    chains = dict(multiread_json("chain/", "*/tokens.json"))
    chains = {k: list(map(lambda x: ERC20Token(**x), v)) for k, v in chains.items()}

    currencies = map(lambda x: Currency(**x), read_json("custody.json"))

    combined = sorted(itertools.chain(coins, erc20_tokens), key=lambda x: x.symbol)
    duplicates = find_duplicates(combined, lambda t: t.symbol)

    if duplicates:
        raise Exception(f"Duplicate elements found: {compress_duplicates(duplicates)}")

    prices = dict(
        coins=read_json(EXT_BLOCKCHAINS_PRICES),
        erc20_tokens=read_json(ETH_EXT_ASSETS_PRICES),
    )
    issues = list(check_currencies(currencies, coins, erc20_tokens, chains, prices))
    
    print("")
    print(reduce(operator.add, map(lambda i: "\n- " + str(i), issues)))
    print("")

    if any(i.is_blocker() for i in issues):
        raise Exception("Blocker issue(s) found")


if __name__ == '__main__':
    main()
