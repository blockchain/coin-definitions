import os
import sys

import json
import argparse

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

def to_bc_format(asset):
    return dict(
        name=asset['name'],
        symbol=asset['symbol'],
        address=asset['id'],
        decimals=asset['decimals'],
        website=asset['website']
    )

def main():
    parser = argparse.ArgumentParser()
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

    # Make sure the asset is in the allowlist and NOT in the denylist:
    assets = filter(lambda x: x['id'].lower() in allowlist, assets)
    assets = filter(lambda x: x['id'].lower() not in denylist, assets)

    # Convert to our format:
    assets = list(map(to_bc_format, assets))

    print(f"Writing {len(assets)} assets to {args.output_file}")
    write_json(assets, args.output_file)


if __name__ == '__main__':
    main()
