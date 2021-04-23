#!/usr/bin/env bash

echo '[+] Initializing submodules...'
git submodule init
git submodule update

echo '[+] Updating submodules to latest master version...'
git submodule foreach git fetch --all
git submodule foreach git reset --hard origin/master
git submodule foreach git checkout master
git submodule foreach git pull

echo '[+] Updating master tokens list...'
cp ethereum-lists/dist/tokens/eth/tokens-eth.json mew-tokens-eth.json
