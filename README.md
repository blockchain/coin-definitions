# Blockchain.com Coins Definitions

## Contents

### L1 Coins

(TBD)

### ERC-20 Tokens List

The file `erc20-tokens-list.json` is a single JSON file that contains the info from each asset listed in https://github.com/trustwallet/assets/tree/master/blockchains/ethereum/assets/, except:

 - those with a status other than "active"
 - those that are NOT listed in the "allowlist" (https://github.com/trustwallet/assets/blob/master/blockchains/ethereum/allowlist.json)
 - those that are listed in the "denylist" (https://github.com/trustwallet/assets/blob/master/blockchains/ethereum/denylist.json)
 - those listed in `erc20-denylist.txt` (used mostly to disambiguate between tokens that have the same symbol)
 - those with either no price or a price of $0 USD, according to https://www.coingecko.com/

Additionally, all assets defined in `overrides/blockchains/ethereum/assets` are added to the dataset (but these are not subject to the filters described above).

For each asset, we include:
 - address (string)
 - decimals (int)
 - logo (string)
 - name (string)
 - symbol (string)
 - website (string)

Example:

```json
{
    "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "decimals": 6,
    "logo": "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/ethereum/assets/0xdAC17F958D2ee523a2206206994597C13D831ec7/logo.png",
    "name": "Tether",
    "symbol": "USDT",
    "website": "https://tether.to"
}
```

## Updating

Just run update.sh:

```
$ bash update.sh
```

This will bring the `trustwallet` repo up to date, and re-build all lists.

## Overriding logos:

### L1s:

(TBD)

### ERC-20s

Add the new file(s) -in PNG format- to the corresponding directory:

NOTE: the address must be in checksum format

```
overrides/blockchains/ethereum/assets/{{token_address}}/logo.json
```

For example:
```
overrides/blockchains/ethereum/assets/0x123151402076fc819B7564510989e475c9cD93CA/logo.png
```

Then run `build.sh` at the root:

```
$ bash buils.sh
```
