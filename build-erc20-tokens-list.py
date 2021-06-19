import os
import sys

import json
import argparse

from dataclasses import asdict, dataclass

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

    def copy(self, address=None,
                   decimals=None,
                   logo=None,
                   name=None,
                   symbol=None,
                   website=None):
        return ERC20Token(
            address or self.address,
            decimals or self.decimals,
            logo or self.logo,
            name or self.name,
            symbol or self.symbol,
            website or self.website
        )


def read_json(path):
    with open(path) as json_file:
        return json.load(json_file)

def write_json(data, path):
    with open(path, "w") as json_file:
        return json.dump(data, json_file, sort_keys=True, indent=4)

def build_assets_list(assets_dir):
    for asset_dir in sorted(os.listdir(assets_dir)):
        asset_info_path = os.path.join(assets_dir, asset_dir, "info.json")

        if not os.path.exists(asset_info_path):
            continue

        yield read_json(asset_info_path)

def build_token_logo(base_path, address):
    asset_path = urljoin(base_path, address + "/")
    return urljoin(asset_path, "logo.png")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("public_assets_dir", help="Path to the PUBLIC assets directory")
    parser.add_argument("assets_dir", help="Path to the assets directory")
    parser.add_argument("allowlist", help="Path to the allow list file")
    parser.add_argument("denylist", help="Path to the allow list file")
    parser.add_argument("output_file", help="Output file name")
    args = parser.parse_args()

    # Build the allow/deny lists:
    allowlist = set(map(lambda x: x.lower(), read_json(args.allowlist)))
    denylist = set(map(lambda x: x.lower(), read_json(args.denylist)))

    # Fetch and parse all info.json files:
    print(f"Reading assets from {args.assets_dir}")
    assets = build_assets_list(args.assets_dir)

    # Keep only the active ones:
    assets = filter(lambda x: x['status'] == 'active', assets)

    # Convert to Token instances:
    tokens = (ERC20Token.from_asset_dict(asset) for asset in assets)

    # Make sure the asset is in the allowlist and NOT in the denylist:
    tokens = filter(lambda x: x.address.lower() in allowlist, tokens)
    tokens = filter(lambda x: x.address.lower() not in denylist, tokens)

    # Inject logos:
    tokens = map(lambda x: x.copy(logo=build_token_logo(args.public_assets_dir, x.address)), tokens)

    # Convert back to plain dicts:
    tokens = list(map(asdict, tokens))

    print(f"Writing {len(tokens)} tokens to {args.output_file}")
    write_json(tokens, args.output_file)


if __name__ == '__main__':
    main()
