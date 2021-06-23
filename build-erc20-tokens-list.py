import os
import sys

import json
import argparse

import itertools
from dataclasses import asdict, dataclass, replace
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
    def from_asset_dict(asset):
        return ERC20Token(
            address=asset['id'],
            decimals=asset['decimals'],
            logo='',
            name=asset['name'],
            symbol=asset['symbol'],
            website=asset['website']
        )

ETHERSCAN_TOKEN_URL = "https://etherscan.io/token/"
COIN_GECKO_TOKEN_PRICE_URL = "https://api.coingecko.com/api/v3/simple/token_price/ethereum"

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

def build_assets_list(assets_dir):
    for asset_dir in sorted(os.listdir(assets_dir)):
        asset_info_path = os.path.join(assets_dir, asset_dir, "info.json")

        if not os.path.exists(asset_info_path):
            continue

        yield read_json(asset_info_path)

def filter_by_market_cap(tokens, prices):
    for token in tokens:
        address = token.address.lower()
        if address not in prices:
            continue
        market_cap = prices[address].get("usd_market_cap", None)
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

def build_token_logo(base_path, address):
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
            market_cap = prices.get(token.address.lower(), {}).get("usd_market_cap", 0.0)
            print(f"# - {urljoin(ETHERSCAN_TOKEN_URL, token.address)} ({token.name}): {token.website}")
            print(f"#   USD Market cap on {now}: ${market_cap:,.2f}")
            print(f"# {token.address}")

def merge_lists(a, b, key):
    to_dict = lambda l: dict((key(x), x) for x in l)
    to_list = lambda d: sorted(d.values(), key=key)
    d = to_dict(a)
    d.update(to_dict(b))
    return to_list(d)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("public_assets_dir", help="Path to the PUBLIC assets directory")
    parser.add_argument("assets_dir", help="Path to the assets directory")
    parser.add_argument("tw_allowlist", help="Path to the allow list file")
    parser.add_argument("tw_denylist", help="Path to the deny list file")
    parser.add_argument("bc_denylist", help="Path to custom blacklist file")
    parser.add_argument("bc_overrides", help="Path to custom overrides file")
    parser.add_argument("output_file", help="Output file name")
    args = parser.parse_args()

    # Build the allow/deny lists:
    tw_allowlist = set(map(lambda x: x.lower(), read_json(args.tw_allowlist)))
    tw_denylist = set(map(lambda x: x.lower(), read_json(args.tw_denylist)))
    bc_denylist = set(map(lambda x: x.lower(), read_txt(args.bc_denylist)))
    bc_overrides = map(lambda x: ERC20Token(**x), read_json(args.bc_overrides))

    # Fetch and parse all info.json files:
    print(f"Reading assets from {args.assets_dir}")
    assets = build_assets_list(args.assets_dir)

    # Keep only the active ones:
    assets = filter(lambda x: x['status'] == 'active', assets)

    # Convert to Token instances:
    tokens = (ERC20Token.from_asset_dict(asset) for asset in assets)

    # Make sure the asset is in the tw_allowlist and NOT in the denylists:
    tokens = filter(lambda x: x.address.lower() in tw_allowlist, tokens)
    tokens = filter(lambda x: x.address.lower() not in tw_denylist, tokens)
    tokens = filter(lambda x: x.address.lower() not in bc_denylist, tokens)

    tokens = list(tokens)
    prices = fetch_all_prices(tokens)

    # Clean up:
    tokens = list(filter_by_market_cap(tokens, prices))
    duplicates = find_duplicates(tokens)

    if duplicates:
        dump_duplicates(duplicates, prices)
        return

    # Inject logos:
    tokens = map(lambda x: replace(x, logo=build_token_logo(args.public_assets_dir, x.address)), tokens)

    # Merge with overrides dict:
    tokens = merge_lists(tokens, bc_overrides, lambda t: t.address)

    # Convert back to plain dicts:
    tokens = list(map(asdict, tokens))

    print(f"Writing {len(tokens)} tokens to {args.output_file}")
    write_json(tokens, args.output_file)


if __name__ == '__main__':
    main()
