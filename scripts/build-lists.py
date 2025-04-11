import argparse
import glob
import itertools
import json
import sys
from dataclasses import asdict
from datetime import datetime
from urllib.parse import urljoin

from coin_gecko import fetch_coin_prices, fetch_token_prices, fetch_coin_descriptions, fetch_token_descriptions, fetch_missing_tokens_for_network, get_coin_by_chain_and_address
from common_classes import Asset, Blockchain, Coin, Token
from statics import BLOCKCHAINS, EXT_BLOCKCHAINS_DENYLIST, EXT_BLOCKCHAINS, EXT_PRICES, FINAL_BLOCKCHAINS_LIST, \
    NETWORKS, EXT_OVERRIDES, EXT_TOKEN_PRICES


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


def find_duplicates(items, key, post_filter=None):
    groups = itertools.groupby(sorted(items, key=key), key)
    groups = [(symbol, list(items)) for symbol, items in groups]
    if post_filter:
        return [(symbol, list(filter(post_filter, items))) for symbol, items in groups if len(items) > 1]
    return [(symbol, items) for symbol, items in groups if len(items) > 1]


def get_duplicates_lines(duplicates, network) -> list[str]:
    lines: list[str] = []
    for symbol, tokens in duplicates:
        lines.append(f"# '{symbol}' is shared by:")
        for token in tokens:
            lines.append(f"# {token.address}")
            lines.append(f"# - Website: {token.website}")
            lines.append(f"# - Explorer: {urljoin(network.explorer_url, token.address)} ({token.name})")
            coingecko_coin = get_coin_by_chain_and_address(network.symbol, token.address)
            if coingecko_coin is None:
                lines.append(f"# - CoinGecko: Not found")
            else:
                lines.append(f"# - CoinGecko: https://www.coingecko.com/en/coins/{coingecko_coin.id} ")
        lines.append(f"#")
    return lines


def dump_duplicates(duplicates, network):
    print(f"Found {len(duplicates)} duplicate symbols:")
    lines = get_duplicates_lines(duplicates, network)
    for line in lines:
        print(line)


def fetch_coins():
    # Fetch and parse all info.json files:
    print(f"Reading blockchains from {BLOCKCHAINS}")
    chains = [Blockchain.from_dict(key, chain)
              for key, chain in read_blockchains(BLOCKCHAINS)]

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


def fetch_tokens(chain):
    # Fetch and parse all info.json files:
    assets_dir = f"assets/blockchains/{chain}/assets/"
    print(f"Reading tokens from {assets_dir}")
    assets = [Asset.from_dict(info) for key, info in read_assets(assets_dir)]

    # Keep only the active ones:
    assets = filter(lambda x: x.status == 'active', assets)

    # Convert to Token instances:
    tokens = (Token.from_asset(asset, chain) for asset in assets)

    return list(tokens)


def fetch_prices():
    coins = fetch_coins()
    prices = {
        "timestamp": datetime.now().isoformat(),
        "prices": fetch_coin_prices(coins)
    }

    token_prices = {
        "timestamp": datetime.now().isoformat(),
        "prices": {}
    }

    for network in NETWORKS:
        tokens = fetch_tokens(network.chain)
        all_token_prices = fetch_token_prices(network, tokens)
        price_per_address = {(token.address + '.' + network.symbol): amount for token, amount in all_token_prices.items()}
        price_per_symbol = {token.with_suffix(network).symbol: amount for token, amount in all_token_prices.items()}
        token_prices["prices"].update(price_per_address)
        prices["prices"].update(price_per_symbol)

    print(f"Writing coin prices to {EXT_PRICES}")
    write_json(prices, EXT_PRICES)
    print(f"Writing token prices to {EXT_TOKEN_PRICES}")
    write_json(token_prices, EXT_TOKEN_PRICES)



def build_coins_list():
    coins = list(map(asdict, fetch_coins()))

    print(f"Writing {len(coins)} coins to {FINAL_BLOCKCHAINS_LIST}")
    write_json(coins, FINAL_BLOCKCHAINS_LIST, sort_keys=False, indent=2)


def merge_token_lists(existing_tokens: list[Token], new_tokens: list[Token], coins: list[Coin]) -> list[Token]:
    merged_list = existing_tokens
    existing_tokens_symbol_map = {token.symbol.lower(): True for token in existing_tokens}
    for coin in coins:
        existing_tokens_symbol_map[coin.symbol.lower()] = True
    for new_token in new_tokens:
        found_token_index = next((i for i, t in enumerate(merged_list) if t.address == new_token.address), None)
        # Token already existing, need update (except for symbol that is immutable)
        if found_token_index:
            new_token.symbol = merged_list[found_token_index].symbol
            merged_list[found_token_index] = new_token
            continue

        base_new_symbol = new_token.symbol
        suffix = 2
        # case duplicate symbol, we'll bump the new token symbol until there is no conflict
        while new_token.symbol.lower() in existing_tokens_symbol_map:
            new_token.symbol = f"{base_new_symbol}{suffix}"
            suffix += 1
        existing_tokens_symbol_map[new_token.symbol.lower()] = True
        merged_list.append(new_token)

    return merged_list


def build_tokens_list(network, fill_from_coingecko=False, ci=False):
    print(f"Generating token files for network \"{network.chain}\"")
    tokens = fetch_tokens(network.chain)

    print(f"Reading {network.symbol} token prices from {EXT_TOKEN_PRICES}")
    token_prices = read_json(EXT_TOKEN_PRICES)

    print(f"Tokens before price filter {len(tokens)}")

    # Clean up by price:
    tokens = list(filter(lambda token: (token.address + "." + network.symbol) in token_prices['prices'], tokens))

    print(f"Tokens after price filter {len(tokens)}")

    # Optionally, fetch tokens from CoinGecko, adding to the current list
    if fill_from_coingecko:
        print(f"Fetching missing tokens from CoinGecko")
        new_tokens = fetch_missing_tokens_for_network(network, tokens)
        print(f"Adding {len(new_tokens)} tokens fetched from CoinGecko")
        tokens += new_tokens

    # Make sure the asset is NOT in the denylist:
    deny_path = f"extensions/blockchains/{network.chain}/denylist.txt"
    bc_denylist = set(map(lambda x: x.lower(), read_txt(deny_path)))
    tokens = filter(lambda x: x.address.lower() not in bc_denylist, tokens)

    # Make sure the asset is valid:
    tokens = filter(lambda x: x.is_valid(), tokens)

    # Merge with extensions:
    extensions_path = f"extensions/blockchains/{network.chain}/assets/"
    print(f"Reading {network.symbol} asset extensions from {extensions_path}")
    extensions = [Asset.from_dict(info) for key, info in read_assets(extensions_path)]
    extensions = map(lambda ext: Token.from_asset(ext, network.chain), extensions)
    tokens = sorted(set(extensions) | set(tokens), key=lambda t: t.address)

    print(f"Reading existing assets in {network.output_file}")
    current_tokens = list(
        map(lambda x: Token(**x).without_suffix(network), read_json(network.output_file)))

    extras = list(map(lambda x: Coin.from_dict(x), read_json("coins.json"))) if network.chain == 'ethereum' else []
    tokens = merge_token_lists(existing_tokens=current_tokens, new_tokens=tokens, coins=extras)

    # Look for duplicates:
    # For ethereum we also check collisions with coins as ethereum tokens does not have suffixes

    duplicates = find_duplicates(tokens + extras, lambda t: t.symbol.lower(), lambda t: isinstance(t, Token))
    if duplicates:
        if ci:
            print(f"Found {len(duplicates)} duplicate tokens in ci mode, Aborting")
            print(duplicates)
            sys.exit(1)
        else:
            dump_duplicates(duplicates, network)
            return

    # Add network suffix before final dump:
    tokens = map(lambda token: token.with_suffix(network), tokens)

    # Convert back to plain dicts:
    tokens = list(map(asdict, tokens))

    print(f"Writing {len(tokens)} tokens to {network.output_file}")
    write_json(tokens, network.output_file)
    # Re-build because denylist got updated
    if duplicates and ci:
        build_tokens_list(network, fill_from_coingecko=fill_from_coingecko, ci=False)

def fill_descriptions_from_overrides():
    text_descriptions = read_json('./description/en.json')
    descriptions_list = read_json('./description/info.json')
    descriptions_overrides = read_json(EXT_OVERRIDES)['descriptions']
    website_urls_overrides = read_json(EXT_OVERRIDES)['website_urls']

    for symbol, description in descriptions_overrides.items():
        text_descriptions[symbol] = description
        existing_description = next((desc for desc in descriptions_list if desc['symbol'] == symbol), None)
        if existing_description:
            existing_description['description'] = description
            existing_description['websiteurl'] = website_urls_overrides.get(symbol) or existing_description['websiteurl']
        else:
            descriptions_list.append({
                'symbol': symbol,
                'description': description,
                'websiteurl': website_urls_overrides.get(symbol) or '',
            })

    write_json(text_descriptions, './description/en.json')
    write_json(sorted(descriptions_list, key=lambda x: x['symbol']), './description/info.json')


def fetch_descriptions():
    coins = list(map(lambda x: Coin.from_dict(x), read_json("coins.json")))
    print(f"Fetching descriptions for {len(coins)} coins")
    descriptions = fetch_coin_descriptions(coins)

    for network in NETWORKS:
        tokens = list(map(lambda x: Token.from_dict(x), read_json(network.output_file)))
        print(f"Fetching descriptions for {len(tokens)} {network.symbol} tokens")
        descriptions.update(fetch_token_descriptions(network, tokens))

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
    fill_descriptions_from_overrides()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ci', action='store_true')
    parser.add_argument('--fetch-prices', action='store_true')
    parser.add_argument('--fetch-descriptions', action='store_true')
    parser.add_argument('--fill-descriptions-from-overrides', action='store_true')
    parser.add_argument('--fill-from-coingecko', action='store_true')
    args = parser.parse_args()

    if args.fetch_prices:
        fetch_prices()
    elif args.fetch_descriptions:
        fetch_descriptions()
    elif args.fill_descriptions_from_overrides:
        fill_descriptions_from_overrides()
    else:
        if not args.ci:
            build_coins_list()
        for network in NETWORKS:
            build_tokens_list(network, args.fill_from_coingecko, args.ci)


if __name__ == '__main__':
    main()
