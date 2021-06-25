#!/usr/bin/env bash

echo '[+] Initializing submodules...'
git submodule init
git submodule update

echo '[+] Updating submodules to latest master version...'
git submodule foreach git checkout master
git submodule foreach git pull

bash build.sh