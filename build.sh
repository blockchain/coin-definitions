#!/usr/bin/env bash

echo '[+] Updating master tokens list...'
python3 scripts/build-lists.py \
	erc20-denylist.txt \
	erc20-tokens-list.json
