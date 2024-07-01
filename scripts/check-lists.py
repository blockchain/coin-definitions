import itertools
import operator
from dataclasses import dataclass
from functools import reduce

from common_classes import Coin, Token
from utils import read_json


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
class CustodyCurrency:
    symbol: str
    displaySymbol: str
    type: str
    nabuSettings: NabuSettings
    hwsSettings: HWSSettings
    removed: bool = False

    def __post_init__(self):
        self.nabuSettings = NabuSettings(**self.nabuSettings)

        if self.hwsSettings:
            self.hwsSettings = HWSSettings(**self.hwsSettings)

    def __str__(self):
        return f"[{self.symbol}, {self.type}]"

    def check(self, ref, prices):
        yield from self.check_symbol()
        yield from self.check_precision(ref)
        yield from self.check_min_confirmations()
        yield from self.check_price(ref, prices)

    def check_symbol(self):
        # Ignore display differences if they match after removing the suffix:
        symbol, _, native = self.symbol.partition(".")
        if symbol != self.displaySymbol:
            yield Warning(self, f"displayed as: {self.displaySymbol}")

    def check_price(self, ref, prices):
        if self.hwsSettings is None:
            return

        minWithdrawal = self.hwsSettings.minWithdrawal

        if minWithdrawal == 0:
            return

        try:
            price = prices[ref.symbol]
        except Exception as e:
            yield Warning(self, f"No price: {e}")
            return

        minWithdrawalValue = minWithdrawal * 1.0 / (10 ** ref.decimals) * price

        if not (0.01 < minWithdrawalValue < 10):
            yield Warning(self, f"minWithdrawal {minWithdrawal} -> "
                                f"${minWithdrawalValue:.3f} not in the $0.01-$10 USD range")

    def check_min_confirmations(self):
        if self.hwsSettings is None:
            return

        # This applies only to ETH or ERC20s on the ETH network; we don't check the minConfirmations
        # on other chains:
        symbol, _, native = self.symbol.partition(".")
        eth_confs = 64
        if (self.symbol == "ETH" or (self.type == "ERC20" and native == "")) and \
                self.hwsSettings.minConfirmations != eth_confs:
            yield Error(self, f"minConfirmations {self.hwsSettings.minConfirmations}, expected {eth_confs}")

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
class Chain:
    chain: str
    displayName: str
    native: str
    tokens: str


def find_duplicates(items, key):
    groups = itertools.groupby(sorted(items, key=key), key)
    groups = [(symbol, list(items)) for symbol, items in groups]
    return [(symbol, items) for symbol, items in groups if len(items) > 1]


def check_logo(coin):
    if coin.logo is None:
        yield Warning(coin, "No logo")


def check_currencies(custody_currencies, coins, eth_erc20_tokens, chains, prices):
    coins = {x.symbol: x for x in coins}
    eth_erc20_tokens = {x.symbol: x for x in eth_erc20_tokens}
    chains = {k: {t.symbol: t for t in v} for k, v in chains.items()}

    for currency in custody_currencies:
        if currency.symbol.upper() != currency.symbol:
            yield Error(currency, f"Contains mix of lower and upper case letters")

        if currency.type == "COIN":
            ref = coins.get(currency.symbol)
        elif currency.type == "ERC20":
            # No "native" (parent symbol) means it's a token in the ETH network;
            # otherwise we must lookup in the appropriate chain:
            symbol, _, native = currency.symbol.partition(".")
            if native == "" or native == "ETH":
                ref = eth_erc20_tokens.get(currency.symbol)
            else:
                ref = chains.get(native).get(currency.symbol)
        elif currency.type == "CELO_TOKEN":
            ref = chains.get("CELO").get(currency.symbol)
        else:
            yield Error(currency, "Invalid type")
            continue

        if ref is None:
            yield Error(currency, "Reference not found")
            continue

        yield from itertools.chain(check_logo(ref), currency.check(ref, prices))


def main():
    coins = list(map(lambda x: Coin.from_dict(x), read_json("coins.json")))
    eth_erc20_tokens = list(map(lambda x: Token.from_dict(x), read_json("erc20-tokens.json")))
    chains = list(map(lambda x: Chain(**x), read_json("chain/list.json")))
    chains = dict((c.native, read_json(c.tokens)) for c in chains)
    chains = {k: list(map(lambda x: Token.from_dict(x), v)) for k, v in chains.items()}
    other_tokens = [token for chain_tokens in chains.values() for token in chain_tokens]

    custody_currencies = map(lambda x: CustodyCurrency(**x), read_json("custody.json"))

    combined = sorted(itertools.chain(coins, eth_erc20_tokens, other_tokens), key=lambda x: x.symbol)
    duplicates = find_duplicates(combined, lambda t: t.symbol.upper())

    if duplicates:
        raise Exception(f"Duplicate elements found: {duplicates}")

    prices = read_json("extensions/prices.json")['prices']
    issues = list(check_currencies(custody_currencies, coins, eth_erc20_tokens, chains, prices))

    print("")
    print(reduce(operator.add, map(lambda i: "\n- " + str(i), issues)))
    print("")

    if any(i.is_blocker() for i in issues):
        raise Exception("Blocker issue(s) found")


if __name__ == '__main__':
    main()
