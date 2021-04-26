#!/usr/bin/env bash

echo '[+] Initializing submodules...'
git submodule init
git submodule update

echo '[+] Updating submodules to latest master version...'
git submodule foreach git checkout master
git submodule foreach git pull

echo '[+] Updating master tokens list...'
python3 build-erc20-tokens-list.py \
	assets/blockchains/ethereum/assets/ \
	assets/blockchains/ethereum/allowlist.json \
	assets/blockchains/ethereum/denylist.json \
	erc20-tokens-list.json
