import glob
import json
import itertools
from dataclasses import dataclass
import requests
import datetime
import os
import re
from typing import Union, Optional, Dict

Timestamp = Union[datetime.datetime, datetime.date, int, float]

DATA_URL = 'https://min-api.cryptocompare.com/data/all/coinlist'


@dataclass
class Coin:
    symbol: str
    name: str
    key: str
    decimals: int
    logo: str

    def __str__(self):
        return f"[{self.symbol}, COIN]"

    def get_price(self, prices):
        return prices[self.symbol]

    def check(self):
        if self.logo is None:
            yield Warning(self, f"No logo")


@dataclass
class ERC20Token:
    address: str
    decimals: int
    displaySymbol: str
    logo: str
    name: str
    symbol: str
    website: str

    def __str__(self):
        return f"[{self.symbol}, ERC20]"

    def get_price(self, prices):
        return prices[self.symbol]

    def check(self):
        if self.logo is None:
            yield Warning(self, f"No logo")


def read_json(path):
    with open(path) as json_file:
        return json.load(json_file)


def multiread_json(base_dir, pattern):
    for target in sorted(glob.glob(base_dir + pattern)):
        key = target.replace(base_dir, '').partition("/")[0]
        yield key, read_json(target)


def compress_duplicates(duplicates):
    return [(symbol, [x.name for x in group]) for symbol, group in duplicates]


def _query_cryptocompare(url: str, errorCheck: bool = True, api_key: str = None) -> Optional[Dict]:
    """
    Query the url and return the result or None on failure.
    :param url: the url
    :param errorCheck: run extra error checks (default: True)
    :returns: respones, or nothing if errorCheck=True
    :api_key: optional, if you want to add an API Key
    """

    api_key_parameter = os.getenv('CRYPTOCOMPARE_API_KEY') if api_key is None else api_key
    api_key_parameter = "&api_key={}".format(api_key) if api_key_parameter is not None else ""

    try:
        response = requests.get(url + api_key_parameter).json()
    except Exception as e:
        print('Error getting coin information. %s' % str(e))
        return None
    if errorCheck and (response.get('Response') == 'Error'):
        print('[ERROR] %s' % response.get('Message'))
        return None
    return response


def write_json(data, path, sort_keys=True, indent=4):
    with open(path, "w") as json_file:
        return json.dump(data, json_file, sort_keys=sort_keys, indent=indent)

def filter_desc(line):
    return re.split(r'Blockchain data provided by:', line, maxsplit=1)[0].strip()


def main():
    coins = list(map(lambda x: Coin(**x), read_json("coins.json")))
    erc20_tokens = list(map(lambda x: ERC20Token(**x), read_json("erc20-tokens.json")))
    crypto_compare_data = _query_cryptocompare(DATA_URL)
    crypto_compare_data = crypto_compare_data['Data']
    chains = dict(multiread_json("chain/", "*/tokens.json"))
    chains = {k: list(map(lambda x: ERC20Token(**x), v)) for k, v in chains.items()}

    map_symbols = set(itertools.chain.from_iterable(
        [map(lambda x: x.symbol, itertools.chain(*chains.values())),
         map(lambda x: x.symbol, coins),
         map(lambda x: x.symbol, erc20_tokens)]))
    dic_list = dict()
    no_symbol = list()
    objectArray = []
    for sym in map_symbols:
        if sym in crypto_compare_data:
            crypto_details = crypto_compare_data[sym]
            desc = dict(symbol=sym)
            if 'AssetWebsiteUrl' in crypto_details:
                desc['websiteurl'] = crypto_details['AssetWebsiteUrl']
            if 'AssetWhitepaperUrl' in crypto_details:
                desc['whitepaper'] = crypto_details['AssetWhitepaperUrl']
            desc_text = filter_desc(crypto_details['Description'])
            dic_list[sym] = desc_text
            desc['description'] = desc_text
            objectArray.append(desc)
        else:
            no_symbol.append(sym)

    write_json(dic_list, './description/en.json')
    write_json(objectArray, './description/info.json')
    print('Warning No Description Found For These:', no_symbol)


if __name__ == '__main__':
    main()
