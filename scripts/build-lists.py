import argparse
import glob
import itertools
import json
from dataclasses import asdict
from datetime import datetime
from urllib.parse import urljoin

from coin_gecko import fetch_coin_prices, fetch_token_prices, fetch_coin_descriptions, fetch_token_descriptions
from common_classes import Asset, Blockchain, Coin, ERC20Token
from statics import BLOCKCHAINS, EXT_BLOCKCHAINS_DENYLIST, EXT_BLOCKCHAINS, EXT_PRICES, FINAL_BLOCKCHAINS_LIST, \
    ERC20_NETWORKS


def read_json(path, comment_marker=None):
    with open(path) as json_file:
        if comment_marker:
            raw_data = "".join(map(lambda l: l.split(comment_marker)[0], json_file.readlines()))
            return json.loads(raw_data)
        else:
            return json.load(json_file)


def read_txt(path):
    with open(path) as txt_file:
        lines = txt_file.readlines()
        lines = [line[:line.find('#')].strip() for line in lines]
        lines = [line for line in lines if line]
        return lines


def write_json(data, path, sort_keys=True, indent=4):
    with open(path, "w") as json_file:
        return json.dump(data, json_file, sort_keys=sort_keys, indent=indent)


def multiread_json(base_dir, pattern, comment_marker=None):
    for target in sorted(glob.glob(base_dir + pattern)):
        key = target.replace(base_dir, '').partition("/")[0]
        yield key, read_json(target, comment_marker=comment_marker)


def read_assets(assets_dir):
    yield from multiread_json(assets_dir, "/*/info.json")


def read_blockchains(blockchains_dir, comment_marker=None):
    yield from multiread_json(blockchains_dir, "/*/info/info.json", comment_marker)


def find_duplicates(items, key):
    groups = itertools.groupby(sorted(items, key=key), key)
    groups = [(symbol, list(items)) for symbol, items in groups]
    return [(symbol, items) for symbol, items in groups if len(items) > 1]


def dump_duplicates(duplicates, explorer_url):
    print(f"Found {len(duplicates)} duplicate symbols:")

    for symbol, tokens in duplicates:
        print(f"# '{symbol}' is shared by:")
        for token in tokens:
            etherscan_url = urljoin(explorer_url, token.address)
            print(f"# - {etherscan_url} ({token.name}): {token.website}")
            print(f"# {token.address}")
        print(f"#")


def fetch_coins():
    # Fetch and parse all info.json files:
    print(f"Reading blockchains from {BLOCKCHAINS}")
    chains = [Blockchain.from_dict(key, chain)
              for key, chain in read_blockchains(BLOCKCHAINS)]

    # ARETH/ARBETH workaround
    for i, n in enumerate(chains):
        if n.symbol == "ARETH":
            chains[i].symbol = "ARBETH"

    # Filter valid & active chains
    chains = filter(lambda x: x.is_valid() and x.is_active(), chains)

    # Build the denylists:
    denylist = set(map(lambda x: (x["symbol"], x["name"]), read_json(EXT_BLOCKCHAINS_DENYLIST)))

    # Make sure the chain is NOT in the denylist:
    chains = filter(lambda x: (x.symbol, x.name) not in denylist, chains)

    # Merge with extensions:
    print(f"Reading blockchain extensions from {EXT_BLOCKCHAINS}")
    extensions = [Blockchain.from_dict(key, chain)
                  for key, chain in read_blockchains(EXT_BLOCKCHAINS, "///")]

    chains = sorted(itertools.chain(chains, extensions), key=lambda x: x.symbol)

    # Convert to Coin instances:
    coins = list(map(Coin.from_chain, chains))

    duplicates = find_duplicates(coins, lambda c: c.symbol.lower())

    if duplicates:
        raise Exception(f"Duplicates found: {duplicates}")

    return list(coins)


def fetch_erc20_tokens(assets_dir, chain):
    # Fetch and parse all info.json files:
    print(f"Reading erc20 assets from {assets_dir}")
    assets = [Asset.from_dict(info) for key, info in read_assets(assets_dir)]

    # Keep only the active ones:
    assets = filter(lambda x: x.status == 'active', assets)

    # Convert to Token instances:
    tokens = (ERC20Token.from_asset(asset, chain) for asset in assets)

    return list(tokens)


def fetch_prices():
    coins = fetch_coins()

    prices = {
        "timestamp": datetime.now().isoformat(),
        "prices": fetch_coin_prices(coins)
    }

    for network in ERC20_NETWORKS:
        tokens = fetch_erc20_tokens(network.assets_dir, network.chain)
        prices["prices"].update(fetch_token_prices(network, tokens))

    print(f"Writing coin prices to {EXT_PRICES}")

    write_json(prices, EXT_PRICES)


def build_coins_list():
    coins = list(map(asdict, fetch_coins()))

    print(f"Writing {len(coins)} coins to {FINAL_BLOCKCHAINS_LIST}")
    write_json(coins, FINAL_BLOCKCHAINS_LIST, sort_keys=False, indent=2)


def build_erc20_tokens_list(erc20_network):
    print(f"Generating token files for network \"{erc20_network.chain}\"")
    tokens = fetch_erc20_tokens(erc20_network.assets_dir, erc20_network.chain)

    print(f"Reading {erc20_network.symbol} asset prices from {EXT_PRICES}")
    prices = read_json(EXT_PRICES)

    print(f"Tokens before price filter {len(tokens)}")

    # Clean up by price:
    tokens = list(filter(lambda token: token.with_suffix(erc20_network).symbol in prices['prices'], tokens))

    print(f"Tokens after price filter {len(tokens)}")

    # Include already selected tokens (to make sure we don't remove a token we had previously selected)
    print(f"Reading existing assets in {erc20_network.output_file}")
    current_tokens = list(
        map(lambda x: ERC20Token(**x).without_suffix(erc20_network), read_json(erc20_network.output_file)))
    tokens = list(set(tokens) | set(current_tokens))

    # Make sure the asset is NOT in the denylist:
    bc_denylist = set(map(lambda x: x.lower(), read_txt(erc20_network.denylist)))
    tokens = filter(lambda x: x.address.lower() not in bc_denylist, tokens)

    # Make sure the asset is valid:
    tokens = filter(lambda x: x.is_valid(), tokens)

    # Merge with extensions:
    print(f"Reading {erc20_network.symbol} asset extensions from {erc20_network.ext_assets_dir}")
    extensions = [Asset.from_dict(info) for key, info in read_assets(erc20_network.ext_assets_dir)]
    extensions = map(lambda ext: ERC20Token.from_asset(ext, erc20_network.chain), extensions)
    tokens = sorted(set(extensions) | set(tokens), key=lambda t: t.address)

    # Look for duplicates:
    duplicates = find_duplicates(tokens, lambda t: t.symbol.lower())

    if duplicates:
        dump_duplicates(duplicates, erc20_network.explorer_url)
        return

    # Add network suffix before final dump:
    tokens = map(lambda token: token.with_suffix(erc20_network), tokens)

    # Convert back to plain dicts:
    tokens = list(map(asdict, tokens))

    print(f"Writing {len(tokens)} tokens to {erc20_network.output_file}")
    write_json(tokens, erc20_network.output_file)


def fetch_descriptions():
    coins = list(map(lambda x: Coin.from_dict(x), read_json("coins.json")))
    print(f"Fetching descriptions for {len(coins)} coins")
    descriptions = fetch_coin_descriptions(coins)

    for erc20_network in ERC20_NETWORKS:
        erc20_tokens = list(map(lambda x: ERC20Token.from_dict(x), read_json(erc20_network.output_file)))
        print(f"Fetching descriptions for {len(erc20_tokens)} {erc20_network.symbol} tokens")
        descriptions.update(fetch_token_descriptions(erc20_network, erc20_tokens))

    text_descriptions = {}
    descriptions_list = []

    for symbol, description in descriptions.items():
        if not description:
            pass
        text_description = description.description
        text_descriptions[symbol] = text_description if text_description else ''
        descriptions_list.append({
            'symbol': symbol,
            'description': text_description,
            'websiteurl': description.website,
        })

    write_json(text_descriptions, './description/en.json')
    write_json(sorted(descriptions_list, key=lambda x: x['symbol']), './description/info.json')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fetch-prices', action='store_true')
    parser.add_argument('--fetch-descriptions', action='store_true')
    args = parser.parse_args()

    if args.fetch_prices:
        fetch_prices()
    elif args.fetch_descriptions:
        fetch_descriptions()
    else:
        build_coins_list()
        for erc20_network in ERC20_NETWORKS:
            build_erc20_tokens_list(erc20_network)


if __name__ == '__main__':
    main()
