#!/usr/bin/env bash

echo '[+] Running checks...'
python3 scripts/check-lists.py \
	currencies.json \
	fiat.json \
	assets/blockchains/ \
	erc20-tokens-list.json