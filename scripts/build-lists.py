import os
import re
import sys
import glob
import json

import argparse
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

    def is_valid(self):
        # At most 6 letters and digits:
        return re.match("^[a-zA-Z0-9]{1,6}$", self.symbol) != None

    @staticmethod
    def from_asset(asset):
        return ERC20Token(
            address=asset.id,
            decimals=asset.decimals,
            logo=build_token_logo(asset.id),
            name=asset.name,
            symbol=asset.symbol,
            website=asset.website
        )

    def __eq__(self, other):
        return self.address == other.address

    def __hash__(self):
        return hash(self.address)

@dataclass
class Coin:
    symbol: str
    name: str
    key: str
    decimals: int
    logo: str

    @staticmethod
    def from_chain(chain):
        return Coin(
            symbol=chain.symbol,
            name=chain.name,
            key=chain.key,
            logo=build_currency_logo(chain.key),
            decimals=chain.decimals
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
    key: str
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
    def from_dict(cls, key, dict_):
        dict_ = dict(dict_.items())
        dict_.update(dict(key=key))
        return build_dataclass_from_dict(cls, dict_)


# ERC-20 params
ETH_ASSETS = "assets/blockchains/ethereum/assets/"

ETH_EXT_ASSETS = "extensions/blockchains/ethereum/assets/"
ETH_EXT_ASSETS_DENYLIST = "extensions/blockchains/ethereum/denylist.txt"

TW_REPO_ROOT = "https://raw.githubusercontent.com/trustwallet/assets/master/"
BC_REPO_ROOT = "https://raw.githubusercontent.com/blockchain/coin-definitions/master/"

# Coin params
BLOCKCHAINS = "assets/blockchains/"

EXT_BLOCKCHAINS = "extensions/blockchains/"
EXT_BLOCKCHAINS_DENYLIST = "extensions/blockchains/denylist.txt"

EXT_PRICES = "extensions/prices.json"

FINAL_BLOCKCHAINS_LIST="coins.json"
FINAL_ERC20_TOKENS_LIST="erc20-tokens.json"

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def read_json(path, comment_marker=None):
    with open(path) as json_file:
        if comment_marker:
            clean_line = lambda l: l.split(comment_marker)[0]
            raw_data = "".join(map(clean_line, json_file.readlines()))
            return json.loads(raw_data)
        else:
            return json.load(json_file)

def read_json_url(url):
    response = request.urlopen(url).read()
    return json.loads(response)

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

def multiread_json(base_dir, pattern, comment_marker=None):
    for target in sorted(glob.glob(base_dir + pattern)):
        key = target.replace(base_dir, '').partition("/")[0]
        yield (key, read_json(target, comment_marker=comment_marker))

def read_assets(assets_dir):
    yield from multiread_json(assets_dir, "/*/info.json")

def read_blockchains(blockchains_dir, comment_marker=None):
    yield from multiread_json(blockchains_dir, "/*/info/info.json", comment_marker)

def cryptocompare_pricemulti(symbols):
    params = {
        "fsyms": ",".join(symbols),
        "tsyms": "USD"
    }
    url = "https://min-api.cryptocompare.com/data/pricemulti" + "?" + parse.urlencode(params)
    response = read_json_url(url)
    if response.get("Response") == "Error":
        raise Exception(response.get("Message"))
    return {curr: price["USD"] for curr, price in response.items()}

def map_chunked(f, items, chunk_size):
    progress = 0
    for chunk in chunks(items, chunk_size):
        yield f(chunk)
        progress += chunk_size
        sys.stdout.write(f"...{int(progress/len(items)*100)}%")
        sys.stdout.flush()
    sys.stdout.write("\n")

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

def dump_duplicates(duplicates):
    print(f"Found {len(duplicates)} duplicate symbols:")

    for symbol, tokens in duplicates:
        print(f"# '{symbol}' is shared by:")
        for token in tokens:
            etherscan_url = urljoin("https://etherscan.io/token/", token.address)
            print(f"# - {etherscan_url} ({token.name}): {token.website}")
            print(f"# {token.address}")
        print(f"#")

def fetch_coins():
    # Fetch and parse all info.json files:
    print(f"Reading blockchains from {BLOCKCHAINS}")
    chains = [Blockchain.from_dict(key, chain)
              for key, chain in read_blockchains(BLOCKCHAINS)]
    chains = filter(lambda x: x.is_valid() and x.is_active(), chains)

    # Build the denylists:
    denylist = set(map(lambda x: (x["symbol"], x["name"]), read_json(EXT_BLOCKCHAINS_DENYLIST)))

    # Keep only the active ones:
    chains = filter(lambda x: x.status == 'active', chains)

    # Make sure the chain is NOT in the denylist:
    chains = filter(lambda x: (x.symbol, x.name) not in denylist, chains)

    # Merge with extensions:
    print(f"Reading blockchain extensions from {EXT_BLOCKCHAINS}")
    extensions = [Blockchain.from_dict(key, chain)
                  for key, chain in read_blockchains(EXT_BLOCKCHAINS, "//")]

    chains = sorted(itertools.chain(chains, extensions), key=lambda x: x.symbol)

    # Convert to Coin instances:
    coins = list(map(Coin.from_chain, chains))

    duplicates = find_duplicates(coins, lambda c: c.symbol)

    if duplicates:
        raise Exception(f"Duplicates found: {duplicates}")

    return list(coins)

def fetch_erc20_tokens():
    # Fetch and parse all info.json files:
    print(f"Reading ETH assets from {ETH_ASSETS}")
    assets = [Asset.from_dict(info) for key, info in read_assets(ETH_ASSETS)]

    # Keep only the active ones:
    assets = filter(lambda x: x.status == 'active', assets)

    # Convert to Token instances:
    tokens = (ERC20Token.from_asset(asset) for asset in assets)

    return list(tokens)

def fetch_prices():
    coins = fetch_coins()
    tokens = fetch_erc20_tokens()

    symbols = list(set([c.symbol for c in coins] + [t.symbol for t in tokens]))

    print(f"Fetching {len(symbols)} exchange pairs")

    prices = dict(
        timestamp=datetime.now().isoformat(),
        prices=dict()
    )

    for chunk in map_chunked(cryptocompare_pricemulti, symbols, 25):
        prices['prices'].update(chunk)

    print(f"Writing coin prices to {EXT_PRICES}")

    write_json(prices, EXT_PRICES)

def build_coins_list():
    coins = list(map(asdict, fetch_coins()))

    print(f"Writing {len(coins)} coins to {FINAL_BLOCKCHAINS_LIST}")
    write_json(coins, FINAL_BLOCKCHAINS_LIST, sort_keys=False, indent=2)

def build_erc20_tokens_list():
    tokens = fetch_erc20_tokens()

    print(f"Reading ETH asset prices from {EXT_PRICES}")
    prices = read_json(EXT_PRICES)

    # Clean up by price:
    tokens = list(filter(lambda token: token.symbol in prices['prices'], tokens))

    # Include already selected tokens (to make sure we don't remove a token we had previously selected)
    print(f"Reading existing assets in {FINAL_ERC20_TOKENS_LIST}")
    current_tokens = list(map(lambda x: ERC20Token(**x), read_json(FINAL_ERC20_TOKENS_LIST)))
    tokens = list(set(tokens) | set(current_tokens))

    # Make sure the asset is NOT in the denylist:
    bc_denylist = set(map(lambda x: x.lower(), read_txt(ETH_EXT_ASSETS_DENYLIST)))
    tokens = filter(lambda x: x.address.lower() not in bc_denylist, tokens)

    # Make sure the asset is valid:
    tokens = filter(lambda x: x.is_valid(), tokens)

    # Merge with extensions:
    print(f"Reading ETH asset extensions from {ETH_EXT_ASSETS}")
    extensions = [Asset.from_dict(info) for key, info in read_assets(ETH_EXT_ASSETS)]
    extensions = map(ERC20Token.from_asset, extensions)
    tokens = sorted(set(extensions) | set(tokens), key=lambda t: t.address)

    # Look for duplicates:
    duplicates = find_duplicates(tokens, lambda t: t.symbol)

    if duplicates:
        dump_duplicates(duplicates)
        return

    # Convert back to plain dicts:
    tokens = list(map(asdict, tokens))

    print(f"Writing {len(tokens)} tokens to {FINAL_ERC20_TOKENS_LIST}")
    write_json(tokens, FINAL_ERC20_TOKENS_LIST)

def build_custom_assets(assets_dir, output_file):
    print(f"Reading custom asset from {assets_dir}")
    assets = [Asset.from_dict(info) for key, info in read_assets(assets_dir)]
    assets = map(ERC20Token.from_asset, assets)
    assets = list(map(asdict, assets))

    print(f"Writing {len(assets)} assets to {output_file}")
    write_json(assets, output_file)

def build_custom_chain_lists():
    chains = ["celo"]

    for chain in chains:
        assets_dir = f"extensions/blockchains/{chain}/assets/"
        output_file = f"chain/{chain}/tokens.json"
        build_custom_assets(assets_dir, output_file)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fetch-prices', action='store_true')
    args = parser.parse_args()

    if args.fetch_prices:
        fetch_prices()
    else:
        build_coins_list()
        build_erc20_tokens_list()
        build_custom_chain_lists()


if __name__ == '__main__':
    main()
