import itertools
import operator
from dataclasses import dataclass
from functools import reduce
from typing import List

from common_classes import Coin, Token
from statics import EXT_PRICES
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

    def check(self, ref: Token | Coin, prices: dict[str, float]):
        yield from self.check_symbol()
        yield from self.check_precision(ref)
        yield from self.check_min_confirmations()
        yield from self.check_price(ref, prices)

    def check_symbol(self):
        # Ignore display differences if they match after removing the suffix:
        symbol, _, native = self.symbol.partition(".")
        if symbol != self.displaySymbol:
            yield Warning(self, f"displayed as: {self.displaySymbol}")

    def check_price(self, ref: Token | Coin, prices: dict[str, float]):
        if self.hwsSettings is None:
            return

        minWithdrawal = self.hwsSettings.minWithdrawal

        if minWithdrawal == 0:
            return

        try:
            price = get_price_from_ref(ref, prices)
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

@dataclass
class Group:
    parentSymbol: str
    childSymbols: List[str]

def find_duplicates(items, key):
    groups = itertools.groupby(sorted(items, key=key), key)
    groups = [(symbol, list(items)) for symbol, items in groups]
    return [(symbol, items) for symbol, items in groups if len(items) > 1]


def check_logo(coin):
    if coin.logo is None:
        yield Warning(coin, "No logo")


def check_groups(
        groups: List[Group],
        custody_currencies: list[CustodyCurrency],
        prices: dict[str, float],
        coins_dict: dict[str, Coin],
        eth_erc20_tokens_dict: dict[str, Token],
        chains_dict: dict[str, dict[str, Token]]
):
    for group in groups:
        if group.parentSymbol in group.childSymbols:
            yield Error(group.parentSymbol, f"also present in childSymbols")
        # This could change but in the meantime that could avoid some mistakes
        if "." in group.parentSymbol:
            yield Error(group.parentSymbol, f"dotted parentSymbol not allowed")
        if len(group.childSymbols) == 0:
            yield Error(group.parentSymbol, f"empty group")

        dotted_group = next((symbol for symbol in group.childSymbols if "." in symbol), None)
        if dotted_group:
            for symbol in group.childSymbols:
                if group.parentSymbol != symbol.split(".")[0]:
                    yield Error(symbol, f"expected {group.parentSymbol} prefix")

        all_group_symbols = [group.parentSymbol] + group.childSymbols
        parent_custody = next(
            (custody_currency for custody_currency in custody_currencies if
             custody_currency.symbol == group.parentSymbol), None)

        if parent_custody is None:
            yield Error(group.parentSymbol, f"defined in groups.json but not in custody.json")
        ref = load_ref(parent_custody.type, parent_custody.symbol, coins_dict, eth_erc20_tokens_dict, chains_dict)
        if ref is None:
            yield Error(group.parentSymbol, f"defined in groups.json but reference not found")

        parent_price = get_price_from_ref(ref, prices)

        if parent_price <= 0:
            yield Error(group.parentSymbol, f"no price defined")
        for symbol in all_group_symbols:
            found_in_custody = next(
                (custody_currency for custody_currency in custody_currencies if custody_currency.symbol == symbol),
                None)

            child_ref = load_ref(parent_custody.type, parent_custody.symbol, coins_dict, eth_erc20_tokens_dict, chains_dict)

            if child_ref is None:
                yield Error(symbol, f"defined in groups.json but reference not found")

            child_price = get_price_from_ref(child_ref, prices)

            if abs(child_price - parent_price) >= 0.01:
                yield Error(symbol, f"too much price diff between parent and child")
            if not found_in_custody:
                yield Error(symbol, f"defined in groups.json but not in custody.json")
            elif parent_custody.nabuSettings.custodialPrecision != found_in_custody.nabuSettings.custodialPrecision:
                yield Error(symbol, f"expected same custodialPrecision as part of the same group")


def load_ref(
        currency_type: str,
        original_symbol: str,
        coins_dict: dict[str, Coin],
        eth_erc20_tokens_dict: dict[str, Token],
        chains_dict: dict[str, dict[str, Token]]
) -> None | Token| Coin:
    ref: None | Token | Coin = None
    if currency_type == "COIN":
        ref = coins_dict.get(original_symbol)
    elif currency_type == "ERC20":
        # No "native" (parent symbol) means it's a token in the ETH network;
        # otherwise we must look up in the appropriate chain:
        symbol, _, native = original_symbol.partition(".")
        if native == "" or native == "ETH":
            ref = eth_erc20_tokens_dict.get(symbol)
        else:
            ref = chains_dict.get(native).get(original_symbol)
    elif currency_type == "CELO_TOKEN":
        ref = chains_dict.get("CELO").get(original_symbol)
    elif currency_type == "SOLANA_TOKEN":
        ref = chains_dict.get("SOL").get(original_symbol)
    elif currency_type == "JETTON":
        ref = chains_dict.get("TON").get(original_symbol)
    elif currency_type == "CARDANO_TOKEN":
        ref = chains_dict.get("ADA").get(original_symbol)
    return ref


def get_price_from_ref(
        ref: Token | Coin,
        prices: dict[str, float],
) -> float:
    if isinstance(ref, Coin):
        return prices[ref.symbol]
    elif isinstance(ref, Token):
        suffix = "ETH"
        fds = ref.symbol.split(".")
        if len(fds) == 2:
            suffix = fds[1]
        return prices[ref.address + "." + suffix]
    else:
        raise Exception("Unexpected type")


def check_currencies(
        custody_currencies: list[CustodyCurrency],
        coins: list[Coin],
        eth_erc20_tokens: list[Token],
        chains: dict[str, list[Token]],
        prices: dict[str, float],
        groups: List[Group]
):
    coins_dict = {x.symbol: x for x in coins}
    eth_erc20_tokens_dict = {x.symbol: x for x in eth_erc20_tokens}
    chains_dict = {k: {t.symbol: t for t in v} for k, v in chains.items()}

    for err in check_groups(groups, custody_currencies, prices, coins_dict, eth_erc20_tokens_dict, chains_dict):
        yield err

    for currency in custody_currencies:
        if currency.symbol.upper() != currency.symbol:
            yield Error(currency, f"Contains mix of lower and upper case letters")

        ref = load_ref(currency.type, currency.symbol, coins_dict, eth_erc20_tokens_dict, chains_dict)

        if ref is None:
            yield Error(currency, "Reference not found")
            continue

        yield from itertools.chain(check_logo(ref), currency.check(ref, prices))


def main():
    groups = list(map(lambda x: Group(**x), read_json("groups.json")))
    coins = list(map(lambda x: Coin.from_dict(x), read_json("coins.json")))
    eth_erc20_tokens = list(map(lambda x: Token.from_dict(x), read_json("erc20-tokens.json")))
    chains = list(map(lambda x: Chain(**x), read_json("chain/list.json")))
    chains = dict((c.native, read_json(c.tokens)) for c in chains)
    chains = {k: list(map(lambda x: Token.from_dict(x), v)) for k, v in chains.items()}
    other_tokens = [token for chain_tokens in chains.values() for token in chain_tokens]

    custody_currencies = list(map(lambda x: CustodyCurrency(**x), read_json("custody.json")))

    combined = sorted(itertools.chain(coins, eth_erc20_tokens, other_tokens), key=lambda x: x.symbol)
    duplicates = find_duplicates(combined, lambda t: t.symbol.upper())

    if duplicates:
        raise Exception(f"Duplicate elements found: {duplicates}")

    print(f"{len(coins)} coins")
    print(f"{len(eth_erc20_tokens)} ETH tokens")
    for (k, v) in chains.items():
        print(f"{len(v)} {k} tokens")
    print(f"Total: {len(combined)}")

    prices = read_json(EXT_PRICES)['prices']
    issues = list(check_currencies(custody_currencies, coins, eth_erc20_tokens, chains, prices, groups))

    print("")
    print(reduce(operator.add, map(lambda i: "\n- " + str(i), issues)))
    print("")

    if any(i.is_blocker() for i in issues):
        raise Exception("Blocker issue(s) found")


if __name__ == '__main__':
    main()
