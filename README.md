# Blockchain.com Coins Definitions

## Contents

### L1 Coins

All know L1 coins are described in the auto-generated file `coins.json`. Each entry contains:

 - symbol: string
 - name: string
 - key: string
 - decimals: int
 - logo: string

The entries are taken from https://github.com/trustwallet/assets/tree/master/blockchains/, except those that are not "active", or those listed in `extensions/blockchains/denylist.txt`. Additionally, all custom blockchains defined in `extensions/blockchains/*/info/info.json` are added to the set.

Logos are taken from the original repo, but can be overriden by adding them into `extensions/blockchains/*/info/logo.png`.

Example: 

```json
  {
    "symbol": "BTC",
    "name": "Bitcoin",
    "decimals": 8,
    "logo": "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/bitcoin/info/logo.png"
  }
```

### ERC-20 Tokens List

The auto-generated file `erc20-tokens.json` is a single JSON file that contains the info from each asset listed in https://github.com/trustwallet/assets/tree/master/blockchains/ethereum/assets/, except:

 - those with a status other than "active"
 - those that are NOT listed in the "allowlist" (https://github.com/trustwallet/assets/blob/master/blockchains/ethereum/allowlist.json)
 - those that are listed in the "denylist" (https://github.com/trustwallet/assets/blob/master/blockchains/ethereum/denylist.json)
 - those listed in `extensions/blockchains/ethereum/denylist.txt` (used mostly to disambiguate between tokens that have the same symbol)
 - those with either no price or a price of $0 USD, according to https://www.coingecko.com/

Additionally, all assets defined in `extensions/blockchains/ethereum/assets` are added to the dataset (but these are not subject to the filters described above).

For each asset, we include:
 - address: string
 - decimals: int
 - logo: string
 - name: string
 - symbol: string
 - website: string

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

### Custodial assets

The file `custody.json` is a list of manually curated assets, combining both L1 coins and ERC20 tokens. Each entry contains:

 - symbol: string
 - displaySymbol: string
 - type: string ('COIN' or 'ERC20')
 - nabuSettings: object
    - custodialPrecision: int
 - hwsSettings: object (nullable)
    - minConfirmations: int
    - minWithdrawal: int
 - removed: bool (optional)

The `hwsSettings` is optional, it's only set when this particular asset is explicitly supported by the HWS.

Example:
```json
  {
    "symbol": "BTC",
    "displaySymbol": "BTC",
    "type": "COIN",
    "custodialPrecision": 8,
    "hwsSettings": {
      "minConfirmations": 2,
      "minWithdrawal": 5460
    }
  }
```

## Updating

To update the definitions, just run `update.sh`:

```
$ bash update.sh
```

This will bring the `trustwallet` repo up to date, and re-build all lists, and check the results. This can possibly lead to conflicts, in case new tokens that use already existing symbols are added, or prices change and tokens that were ignored previously are not anymore.

## Overriding logos:

For L1s, add the new file(s) to the corresponding directory (L1 coins are referred to by name)

```
extensions/blockchains/{{blockchain}}/info/logo.png
```

For ERC-20s, this is where new logos must be put: (NOTE: the address must be in checksum format)

```
extensions/blockchains/ethereum/assets/{{token_address}}/logo.png
```

_For example:_

```
extensions/blockchains/ethereum/assets/0x123151402076fc819B7564510989e475c9cD93CA/logo.png
```

Then run `build.sh --regen` at the root:

```
$ bash build.sh --regen
```

This will re-generate both `coins.json` and `erc20-tokens.json`.