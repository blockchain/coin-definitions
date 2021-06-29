import os
import sys

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
class Asset:
    id: str
    decimals: int
    name: str
    symbol: str
    website: str
    status: str

    @classmethod
    def from_dict(cls, dict_):
        class_fields = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in dict_.items() if k in class_fields})


ETHERSCAN_TOKEN_URL = "https://etherscan.io/token/"
COIN_GECKO_TOKEN_PRICE_URL = "https://api.coingecko.com/api/v3/simple/token_price/ethereum"

ETH_ASSETS = "assets/blockchains/ethereum/assets/"
ETH_ASSETS_OVERRIDES = "overrides/blockchains/ethereum/assets/"
ETH_ASSETS_ALLOWLIST = "assets/blockchains/ethereum/allowlist.json"
ETH_ASSETS_DENYLIST = "assets/blockchains/ethereum/denylist.json"

PUBLIC_ETH_ASSETS_DIR = "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/ethereum/assets/"
PUBLIC_ETH_ASSETS_OVERRIDES_DIR = "https://raw.githubusercontent.com/blockchain/coin-definitions/master/overrides/blockchains/ethereum/assets/"

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def read_json(path):
    with open(path) as json_file:
        return json.load(json_file)

def read_txt(path):
    with open(path) as txt_file:
        lines = txt_file.readlines()
        lines = [line[:line.find('#')].strip() for line in lines]
        lines = [line for line in lines if line]
        return lines

def write_json(data, path):
    with open(path, "w") as json_file:
        return json.dump(data, json_file, sort_keys=True, indent=4)

def read_assets(assets_dir):
    for asset_dir in sorted(os.listdir(assets_dir)):
        asset_info_path = os.path.join(assets_dir, asset_dir, "info.json")

        if not os.path.exists(asset_info_path):
            continue

        yield read_json(asset_info_path)

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
    if os.path.exists(os.path.join(ETH_ASSETS_OVERRIDES, address, "logo.png")):
        base_path = PUBLIC_ETH_ASSETS_OVERRIDES_DIR
    else:
        base_path = PUBLIC_ETH_ASSETS_DIR
    asset_path = urljoin(base_path, address + "/")
    return urljoin(asset_path, "logo.png")

def find_duplicates(tokens):
    groups = itertools.groupby(sorted(tokens, key=lambda t: t.symbol), lambda t: t.symbol)
    groups = [(symbol, list(tokens)) for symbol, tokens in groups]
    return [(symbol, tokens) for symbol, tokens in groups if len(tokens) > 1]

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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bc_denylist", help="Path to custom blacklist file")
    parser.add_argument("output_file", help="Output file name")
    args = parser.parse_args()

    # Build the allow/deny lists:
    tw_allowlist = set(map(lambda x: x.lower(), read_json(ETH_ASSETS_ALLOWLIST)))
    tw_denylist = set(map(lambda x: x.lower(), read_json(ETH_ASSETS_DENYLIST)))
    bc_denylist = set(map(lambda x: x.lower(), read_txt(args.bc_denylist)))

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
    duplicates = find_duplicates(tokens)

    if duplicates:
        dump_duplicates(duplicates, prices)
        return

    # Merge with overrides:
    print(f"Reading ETH asset overrides from {ETH_ASSETS_OVERRIDES}")
    bc_overrides = map(lambda x: Asset.from_dict(x), read_assets(ETH_ASSETS_OVERRIDES))
    bc_overrides = map(ERC20Token.from_asset, bc_overrides)
    tokens = sorted(itertools.chain(tokens, bc_overrides), key=lambda t: t.address)

    # Inject logos:
    tokens = map(lambda x: replace(x, logo=build_token_logo(x.address)), tokens)

    # Convert back to plain dicts:
    tokens = list(map(asdict, tokens))

    print(f"Writing {len(tokens)} tokens to {args.output_file}")
    write_json(tokens, args.output_file)


if __name__ == '__main__':
    main()
