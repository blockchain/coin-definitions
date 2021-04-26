# Blockchain.com Coins Definitions

## L1 Coins

(TBD)

## ERC-20 Tokens List

The file `erc20-tokens-list.json` is a single JSON file that contains the info from each asset listed in https://github.com/trustwallet/assets/tree/master/blockchains/ethereum/assets/, except:

 - those with a status other than "active"
 - those that are NOT listed in the "allowlist" (https://github.com/trustwallet/assets/blob/master/blockchains/ethereum/allowlist.json)
 - those that are listed in the "denylist" (https://github.com/trustwallet/assets/blob/master/blockchains/ethereum/denylist.json)

For each asset, we include:
 - name (string)
 - symbol (string)
 - address (string)
 - decimals (int)
 - website (string)

### Updating

Just run update.sh:

```
$ bash update.sh
```