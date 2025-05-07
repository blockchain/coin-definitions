import glob
import json
import sys
from typing import List, Any, Dict, Tuple, TypeVar, Callable, Generator
import bech32
import hashlib

T = TypeVar('T')
R = TypeVar('R')

def chunks(lst: List[T], n: int) -> Generator[List[T], None, None]:
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def map_chunked(f: Callable[[List[T]], R], items: List[T], chunk_size: int) -> Generator[R, None, None]:
    progress = 0
    for chunk in chunks(items, chunk_size):
        yield f(chunk)
        progress += len(chunk)
        sys.stdout.write(f"...{int(progress / len(items) * 100)}%")
        sys.stdout.flush()
    sys.stdout.write("\n")

def read_json(path: str) -> Dict[str, Any]:
    with open(path) as json_file:
        return json.load(json_file)

def multiread_json(base_dir: str, pattern: str) -> Generator[Tuple[str, Dict[str, Any]], None, None]:
    for target in sorted(glob.glob(base_dir + pattern)):
        key = target.replace(base_dir, '').partition("/")[0]
        yield key, read_json(target)

def encode_cardano_fingerprint(policy_id: str, asset_name_hex: str) -> str:
    policy_id_bytes = bytes.fromhex(policy_id)
    asset_name_bytes = bytes.fromhex(asset_name_hex)
    asset_id_bytes = policy_id_bytes + asset_name_bytes

    fingerprint_bytes = hashlib.blake2b(asset_id_bytes, digest_size=20).digest()
    data = bech32.convertbits(fingerprint_bytes, 8, 5)
    fingerprint = bech32.bech32_encode('asset', data)

    return fingerprint

def filter_cardano_tokens_by_price(tokens, prices):
    fingerprint_map = {}
    for price_key in prices['prices']:
        if not price_key.endswith(".ADA"):
            continue
        token_id = price_key.split(".")[0]
        if "-" not in token_id:
            continue
        policy_id, asset_name_hex = token_id.split("-")
        fingerprint = encode_cardano_fingerprint(policy_id, asset_name_hex)
        fingerprint_map[fingerprint] = token_id

    filtered_tokens = []
    for token in tokens:
        if token.address in fingerprint_map:
            token.address = fingerprint_map[token.address]
            filtered_tokens.append(token)

    return filtered_tokens

def get_cardano_tokens_by_id(tokens, coin_list):
    # here we handle different cases when contract address in coingecko is sometimes considered as:
    # 1- the asset_id (policy_id + asset_name_hex).
    # 2- the policy_id and missing the asset_name_hex
    # 3- the fingerprint (in hex or readable)

    tokens_by_id = {}
    fingerprint_to_coin = {}

    for asset_id, coin in coin_list.items():
        # scenario-1: as the fingerprint(hex or readable)
        if len(asset_id) < 56:
            try:
                hrp, data = bech32.bech32_decode(asset_id)
                if hrp == "asset":
                    fingerprint_to_coin[asset_id] = (coin, asset_id)
                    continue
            except Exception:
                pass

            try:
                fingerprint_bytes = bytes.fromhex(asset_id)
                fingerprint_words = bech32.convertbits(fingerprint_bytes, 8, 5)
                fingerprint = bech32.bech32_encode("asset", fingerprint_words)
                fingerprint_to_coin[fingerprint] = (coin, fingerprint)
                continue
            except Exception:
                continue  # Skip invalid entries

        # scenario-2: as the policy_id
        elif len(asset_id) == 56:
            policy_id = asset_id
            asset_name_hex = coin.symbol.upper().encode("utf-8").hex()

        # scenario-3: as the asset_id (polic_id + asset_name_hex)
        else:
            policy_id = asset_id[:56]
            asset_name_hex = asset_id[56:]

        fingerprint = encode_cardano_fingerprint(policy_id, asset_name_hex)
        asset_id = f"{policy_id}-{asset_name_hex}"
        fingerprint_to_coin[fingerprint] = (coin, asset_id)

    for token in tokens:
        coin_to_asset = fingerprint_to_coin.get(token.address)
        if coin_to_asset:
            coin, asset_id = coin_to_asset
            token.address = asset_id
            tokens_by_id.setdefault(coin.id, []).append(token)

    return tokens_by_id
