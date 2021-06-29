import os
import sys

import json

import itertools
from dataclasses import asdict, dataclass, fields, replace
from functools import reduce
from datetime import datetime

from urllib import parse, request
from urllib.parse import urljoin

@dataclass
class ERC20Token:
    address: str
    decimals: int
    logo: str
    name: str
    symbol: str
    website: str

    @staticmethod
    def from_asset(asset):
        return ERC20Token(
            address=asset.id,
            decimals=asset.decimals,
            logo='',
            name=asset.name,
            symbol=asset.symbol,
            website=asset.website
        )

@dataclass
class Currency:
    symbol: str
    name: str
    type: str
    decimals: int
    logo: str

    @staticmethod
    def from_keyed_chain(kc):
        return Currency(
            symbol=kc.chain.symbol,
            name=kc.chain.name,
            logo=build_currency_logo(kc.key),
            type="COIN",
            decimals=kc.chain.decimals,
        )

def build_dataclass_from_dict(cls, dict_):
    class_fields = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in dict_.items() if k in class_fields})

@dataclass
class Asset:
    id: str
    decimals: int
    name: str
    symbol: str
    website: str
    status: str

    @classmethod
    def from_dict(cls, dict_):
        return build_dataclass_from_dict(cls, dict_)

@dataclass
class Blockchain:
    name: str
    symbol: str = None
    decimals: int = None
    status: str = None

    def is_valid(self):
        return self.symbol is not None and \
               self.decimals is not None and \
               self.status is not None

    def is_active(self):
        return self.status == 'active'

    def is_removed(self):
        return self.status == 'removed'

    @classmethod
    def from_dict(cls, dict_):
        return build_dataclass_from_dict(cls, dict_)

@dataclass
class KeyedChain:
    key: str
    chain: Blockchain

# External URLs
ETHERSCAN_TOKEN_URL = "https://etherscan.io/token/"
COIN_GECKO_TOKEN_PRICE_URL = "https://api.coingecko.com/api/v3/simple/token_price/ethereum"

# ERC-20 params
ETH_ASSETS = "assets/blockchains/ethereum/assets/"
ETH_ASSETS_ALLOWLIST = "assets/blockchains/ethereum/allowlist.json"
ETH_ASSETS_DENYLIST = "assets/blockchains/ethereum/denylist.json"

ETH_EXT_ASSETS = "extensions/blockchains/ethereum/assets/"
ETH_EXT_ASSETS_DENYLIST = "extensions/blockchains/ethereum/denylist.txt"

TW_REPO_ROOT = "https://raw.githubusercontent.com/trustwallet/assets/master/"
BC_REPO_ROOT = "https://raw.githubusercontent.com/blockchain/coin-definitions/master/"

# Currency params
BLOCKCHAINS = "assets/blockchains/"

EXT_BLOCKCHAINS = "extensions/blockchains/"
EXT_BLOCKCHAINS_DENYLIST = "extensions/blockchains/denylist.txt"


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def read_json(path, comment_marker=None):
    with open(path) as json_file:
        clean_line = lambda l: l if comment_marker is None else l.split(comment_marker)[0]
        raw_data = "".join(map(clean_line, json_file.readlines()))
        return json.loads(raw_data)

def read_txt(path):
    with open(path) as txt_file:
        lines = txt_file.readlines()
        lines = [line[:line.find('#')].strip() for line in lines]
        lines = [line for line in lines if line]
        return lines

def write_json(data, path, sort_keys=True, indent=4):
    with open(path, "w") as json_file:
        return json.dump(data, json_file, sort_keys=sort_keys, indent=indent)

def write_txt(data, path):
    with open(path, "w") as txt_file:
        return txt_file.write(data)

def read_assets(assets_dir):
    for asset_dir in sorted(os.listdir(assets_dir)):
        asset_info_path = os.path.join(assets_dir, asset_dir, "info.json")

        if not os.path.exists(asset_info_path):
            continue

        yield read_json(asset_info_path)

def read_blockchains(blockchains_dir, comment_marker=None):
    for blockchain_dir in sorted(os.listdir(blockchains_dir)):
        info_path = os.path.join(blockchains_dir, blockchain_dir, "info/info.json")

        if not os.path.exists(info_path):
            continue

        yield (blockchain_dir, read_json(info_path, comment_marker=comment_marker))

def filter_by_price(tokens, prices):
    for token in tokens:
        address = token.address.lower()
        if address not in prices:
            continue
        market_cap = prices[address].get("usd", None)
        if market_cap is not None and market_cap > 0:
            yield token

def fetch_token_prices(addresses):
    params = {
        "contract_addresses": ",".join(addresses),
        "vs_currencies": "USD",
        "include_market_cap": "true"
    }
    url = COIN_GECKO_TOKEN_PRICE_URL + "?" + parse.urlencode(params)
    response = request.urlopen(url).read()
    return json.loads(response)

def fetch_all_prices(tokens):
    print(f"Fetching {len(tokens)} pairs from {COIN_GECKO_TOKEN_PRICE_URL}")
    ret = {}
    progress = 0
    for chunk in chunks(tokens, 50):
        ret.update(fetch_token_prices([t.address for t in chunk]))
        progress += 50
        sys.stdout.write(f"...{int(progress/len(tokens)*100)}%")
        sys.stdout.flush()
    sys.stdout.write("\n")
    return ret

def build_token_logo(address):
    if os.path.exists(os.path.join(ETH_EXT_ASSETS, address, "logo.png")):
        base_path = BC_REPO_ROOT + "extensions/blockchains/ethereum/assets/"
    else:
        base_path = TW_REPO_ROOT + "blockchains/ethereum/assets/"
    asset_path = urljoin(base_path, address + "/")
    return urljoin(asset_path, "logo.png")

def build_currency_logo(key):
    if os.path.exists(os.path.join(EXT_BLOCKCHAINS, key, "info", "logo.png")):
        return BC_REPO_ROOT + os.path.join(EXT_BLOCKCHAINS, key, "info", "logo.png")
    elif os.path.exists(os.path.join(BLOCKCHAINS, key, "info", "logo.png")):
        return TW_REPO_ROOT + os.path.join("blockchains", key, "info", "logo.png")
    else:
        return None

def find_duplicates(items, key):
    groups = itertools.groupby(sorted(items, key=key), key)
    groups = [(symbol, list(items)) for symbol, items in groups]
    return [(symbol, items) for symbol, items in groups if len(items) > 1]

def dump_duplicates(duplicates, prices):
    print(f"Found {len(duplicates)} duplicate symbols:")

    tokens = reduce(lambda a, x: a + x[1], duplicates, [])
    addresses = [x.address for x in tokens]
    now = datetime.now().isoformat()

    for symbol, tokens in duplicates:
        print(f"# '{symbol}' is shared by:")
        for token in tokens:
            price = prices.get(token.address.lower(), {})
            usd = price.get("usd")
            usd_market_cap = price.get("usd_market_cap")
            print(f"# - {urljoin(ETHERSCAN_TOKEN_URL, token.address)} ({token.name}): {token.website}")
            print(f"#   Price: ${usd:,.6f} Market cap: ${usd_market_cap:,.2f} ({now})")
            print(f"# {token.address}")


def build_currencies_list(output_file):
    # Fetch and parse all info.json files:
    print(f"Reading blockchains from {BLOCKCHAINS}")
    chains = [KeyedChain(key, Blockchain.from_dict(chain))
              for key, chain in read_blockchains(BLOCKCHAINS)]
    chains = filter(lambda x: x.chain.is_valid() and x.chain.is_active(), chains)

    # Build the denylists:
    denylist = set(map(lambda x: (x["symbol"], x["name"]), read_json(EXT_BLOCKCHAINS_DENYLIST)))

    # Keep only the active ones:
    chains = filter(lambda x: x.chain.status == 'active', chains)

    # Make sure the chain is NOT in the denylist:
    chains = filter(lambda x: (x.chain.symbol, x.chain.name) not in denylist, chains)

    # Merge with extensions:
    print(f"Reading blockchain extensions from {EXT_BLOCKCHAINS}")
    extensions = [KeyedChain(key, Blockchain.from_dict(chain))
                  for key, chain in read_blockchains(EXT_BLOCKCHAINS, "//")]

    chains = sorted(itertools.chain(chains, extensions), key=lambda t: t.chain.symbol)

    # Convert to Currency instances:
    currencies = list(map(Currency.from_keyed_chain, chains))

    duplicates = find_duplicates(currencies, lambda c: c.symbol)

    if duplicates:
        raise Exception(f"Duplicates found: {[key for key, group in duplicates]}")

    # Convert back to plain dicts:
    currencies = list(map(asdict, currencies))

    print(f"Writing {len(currencies)} currencies to {output_file}")
    write_json(currencies, output_file, sort_keys=False, indent=2)


def build_erc20_list(output_file):
    # Build the allow/deny lists:
    tw_allowlist = set(map(lambda x: x.lower(), read_json(ETH_ASSETS_ALLOWLIST)))
    tw_denylist = set(map(lambda x: x.lower(), read_json(ETH_ASSETS_DENYLIST)))
    bc_denylist = set(map(lambda x: x.lower(), read_txt(ETH_EXT_ASSETS_DENYLIST)))

    # Fetch and parse all info.json files:
    print(f"Reading ETH assets from {ETH_ASSETS}")
    assets = map(lambda x: Asset.from_dict(x), read_assets(ETH_ASSETS))

    # Keep only the active ones:
    assets = filter(lambda x: x.status == 'active', assets)

    # Convert to Token instances:
    tokens = (ERC20Token.from_asset(asset) for asset in assets)

    # Make sure the asset is in the tw_allowlist and NOT in the denylists:
    tokens = filter(lambda x: x.address.lower() in tw_allowlist, tokens)
    tokens = filter(lambda x: x.address.lower() not in tw_denylist, tokens)
    tokens = filter(lambda x: x.address.lower() not in bc_denylist, tokens)

    tokens = list(tokens)
    prices = fetch_all_prices(tokens)

    # Clean up:
    tokens = list(filter_by_price(tokens, prices))
    duplicates = find_duplicates(tokens, lambda t: t.symbol)

    if duplicates:
        dump_duplicates(duplicates, prices)
        return

    # Merge with extensions:
    print(f"Reading ETH asset extensions from {ETH_EXT_ASSETS}")
    extensions = map(lambda x: Asset.from_dict(x), read_assets(ETH_EXT_ASSETS))
    extensions = map(ERC20Token.from_asset, extensions)
    tokens = sorted(itertools.chain(tokens, extensions), key=lambda t: t.address)

    # Inject logos:
    tokens = map(lambda x: replace(x, logo=build_token_logo(x.address)), tokens)

    # Convert back to plain dicts:
    tokens = list(map(asdict, tokens))

    print(f"Writing {len(tokens)} tokens to {output_file}")
    write_json(tokens, output_file)


def main():
    build_currencies_list("currencies.json")
    build_erc20_list("erc20-tokens-list.json")


if __name__ == '__main__':
    main()
