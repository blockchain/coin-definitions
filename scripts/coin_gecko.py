import os
import warnings
from dataclasses import dataclass
from typing import Self

import requests
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

from common_classes import build_dataclass_from_dict, Description
from utils import map_chunked

BATCH_SIZE = 250

coin_mappings = {
    "ADA": "cardano",
    "ALGO": "algorand",
    "AR": "arweave",
    "ATOM": "cosmos",
    "AVAX": "avalanche-2",
    "BCH": "bitcoin-cash",
    "BNB": "binancecoin",
    "BSV": "bitcoin-cash-sv",
    "BTC": "bitcoin",
    "CELO": "celo",
    "CLOUT": "deso",
    "DASH": "dash",
    "DCR": "decred",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "EOS": "eos",
    "ETC": "ethereum-classic",
    "ETH": "ethereum",
    "EVER": "everscale",
    "FIL": "filecoin",
    "KAVA": "kava",
    "KIN": "kin",
    "KLAY": "klay-token",
    "LTC": "litecoin",
    "LUNA": "terra-luna-2",
    "MATIC.MATIC": "matic-network",
    "MIOTA": "iota",
    "MOB": "mobilecoin",
    "MTRG": "meter",
    "NEAR": "near",
    "SOL": "solana",
    "STX": "blockstack",
    "TFUEL": "theta-fuel",
    "THETA": "theta-token",
    "TON": "the-open-network",
    "TRX": "tron",
    "XLM": "stellar",
    "XMR": "monero",
    "XRP": "ripple",
    "XTZ": "tezos",
    "ZEC": "zcash",
    "ZIL": "zilliqa",
}

network_mappings = {
    "ARBETH": "arbitrum-one",
    "AVAX": "avalanche",
    "BNB": "binance-smart-chain",
    "CELO": "celo",
    "CHZ": "chiliz",
    "ETH": "ethereum",
    "MATIC": "polygon-pos",
    "OP": "optimistic-ethereum",
    "TRX": "tron",
}


@dataclass
class Coin:
    id: str
    symbol: str
    name: str
    platforms: dict[str, str]

    @classmethod
    def from_dict(cls, dict_: object) -> Self:
        return build_dataclass_from_dict(cls, dict_)


@dataclass
class Market:
    id: str
    current_price: float

    @classmethod
    def from_dict(cls, dict_: object) -> Self:
        return build_dataclass_from_dict(cls, dict_)


class CoinGeckoAPIClient:
    API_KEY = os.getenv('COINGECKO_API_KEY')
    BASE_URL = "https://api.coingecko.com/api/v3/" if API_KEY is None else "https://pro-api.coingecko.com/api/v3/"

    @staticmethod
    def fetch_usd_markets(ids: list[str]) -> list[Market]:
        try:
            response = requests.get(
                f"{CoinGeckoAPIClient.BASE_URL}coins/markets?x_cg_pro_api_key={CoinGeckoAPIClient.API_KEY}&vs_currency=usd&ids={','.join(ids)}&per_page={BATCH_SIZE}"
            ).json()
            return [Market.from_dict(x) for x in response]
        except Exception as e:
            print(f'Error fetching CoinGecko prices: {str(e)}')
            return []

    @staticmethod
    def get_coin_list() -> list[Coin]:
        try:
            response = requests.get(
                f"{CoinGeckoAPIClient.BASE_URL}coins/list?x_cg_pro_api_key={CoinGeckoAPIClient.API_KEY}&include_platform=true").json()
            return [Coin.from_dict(x) for x in response]
        except Exception as e:
            print(f'Error fetching CoinGecko coin list: {str(e)}')
            return []

    warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

    @staticmethod
    def get_coin_description(coin_id: str) -> (str, Description | None):
        if type(coin_id) is list:
            coin_id = coin_id[0]
        try:
            response = requests.get(
                f"{CoinGeckoAPIClient.BASE_URL}coins/{coin_id}?x_cg_pro_api_key={CoinGeckoAPIClient.API_KEY}&localization=false&tickers=false&market_data=false&community_data=false&developer_data=false&sparkline=false"
            ).json()
            description_text = response.get('description', {}).get('en', None)
            website = response.get('links', {}).get('homepage', [None])[0]

            return coin_id, Description(
                description=BeautifulSoup(description_text, 'html.parser').text,
                website=website
            )
        except Exception as e:
            print(f'Error fetching CoinGecko prices: {str(e)}')
            return coin_id, None


coin_list = CoinGeckoAPIClient.get_coin_list()
coin_list_by_id = {}
coin_list_by_platform_and_address = {}

for coin in coin_list:
    coin_list_by_id[coin.id] = coin
    for network, address in coin.platforms.items():
        if address:
            coin_list_by_platform_and_address[(network, address.lower())] = coin


def get_coin_by_id(coin_symbol):
    coin_gecko_id = coin_mappings.get(coin_symbol)
    if coin_gecko_id is None:
        return None
    return coin_list_by_id.get(coin_gecko_id, None)


def get_coin_by_chain_and_address(chain, token_address):
    network_id = network_mappings.get(chain, None)
    if network_id is None:
        return None
    return coin_list_by_platform_and_address.get((network_id, token_address.lower()), None)


def get_coins_by_id(coins):
    coins_by_id = {}
    for coin in coins:
        coin_gecko_id = coin_mappings.get(coin.symbol)
        if coin_gecko_id is not None:
            coins_by_id[coin_gecko_id] = coin
    return coins_by_id


def get_tokens_by_id(network, tokens):
    tokens_by_id = {}
    network_coin_gecko_id = network_mappings.get(network.symbol)
    if network_coin_gecko_id is not None:
        for token in tokens:
            coin = coin_list_by_platform_and_address.get((network_coin_gecko_id, token.address.lower()))
            if coin is not None:
                tokens_by_id[coin.id] = token
    return tokens_by_id


def fetch_coin_prices(coins):
    coins_by_id = get_coins_by_id(coins)
    prices = {}
    for batch in map_chunked(CoinGeckoAPIClient.fetch_usd_markets, list(coins_by_id.keys()), BATCH_SIZE):
        for market in batch:
            coin = coins_by_id.get(market.id)
            if coin is not None:
                prices[coin.symbol] = market.current_price
    return prices


def fetch_token_prices(network, tokens):
    tokens_by_id = get_tokens_by_id(network, tokens)
    prices = {}
    for batch in map_chunked(CoinGeckoAPIClient.fetch_usd_markets, list(tokens_by_id.keys()), BATCH_SIZE):
        for market in batch:
            token = tokens_by_id[market.id]
            if token is not None:
                prices[token.with_suffix(network).symbol] = market.current_price
    return prices


def fetch_coin_descriptions(coins):
    coins_by_id = get_coins_by_id(coins)
    descriptions = {}
    for id, description in map_chunked(CoinGeckoAPIClient.get_coin_description, list(coins_by_id.keys()), 1):
        if description is not None:
            coin = coins_by_id[id]
            descriptions[coin.symbol] = description
    return descriptions


def fetch_token_descriptions(network, tokens):
    tokens_by_id = get_tokens_by_id(network, tokens)
    descriptions = {}
    for id, description in map_chunked(CoinGeckoAPIClient.get_coin_description, list(tokens_by_id.keys()), 1):
        if description is not None:
            token = tokens_by_id[id]
            descriptions[token.symbol] = description
    return descriptions
