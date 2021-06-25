#!/usr/bin/env bash

echo '[+] Updating master tokens list...'
python3 scripts/build-erc20-tokens-list.py \
	https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/ethereum/assets/ \
	assets/blockchains/ethereum/assets/ \
	assets/blockchains/ethereum/allowlist.json \
	assets/blockchains/ethereum/denylist.json \
	erc20-denylist.txt \
	erc20-overrides.json \
	erc20-tokens-list.json
