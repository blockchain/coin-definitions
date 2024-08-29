import os
import warnings
from dataclasses import dataclass
from typing import Self

import requests
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from web3 import Web3

from common_classes import build_dataclass_from_dict, Description, Token
from utils import map_chunked

BATCH_SIZE = 250

coin_mappings = {
    "ADA": "cardano",
    "AKT": "akash-network",
    "ALGO": "algorand",
    "APT": "aptos",
    "AR": "arweave",
    "ARBETH": "ethereum",
    "ATOM": "cosmos",
    "AVAX": "avalanche-2",
    "BCH": "bitcoin-cash",
    "BLD": "agoric",
    "BASEETH": "ethereum",
    "BNB": "binancecoin",
    "BSV": "bitcoin-cash-sv",
    "BTC": "bitcoin",
    "CANTO": "canto",
    "CELO": "celo",
    "CLOUT": "deso",
    "CMDX": "comdex",
    "DASH": "dash",
    "DCR": "decred",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "EGLD": "elrond-erd-2",
    "EOS": "eos",
    "ETC": "ethereum-classic",
    "ETH": "ethereum",
    "ETHW": "ethereum-pow-iou",
    "EVER": "everscale",
    "FIL": "filecoin",
    "FSN": "fsn",
    "HBAR": "hedera-hashgraph",
    "IOTX": "iotex",
    "IRIS": "iris-network",
    "JUNO": "juno-network",
    "KAVA": "kava",
    "KIN": "kin",
    "KLAY": "klay-token",
    "KUJI": "kujira",
    "LTC": "litecoin",
    "LUNA": "terra-luna-2",
    "MARS": "mars-protocol-a7fcbcfb-fd61-4017-92f0-7ee9f9cc6da3",
    "MATIC.MATIC": "matic-network",
    "MIOTA": "iota",
    "MOB": "mobilecoin",
    "MTRG": "meter",
    "NEAR": "near",
    "OETH": "ethereum",
    "SCRT": "secret",
    "SOL": "solana",
    "SOMM": "sommelier",
    "STARS": "stargaze",
    "STRD": "stride",
    "STX": "blockstack",
    "SUI": "sui",
    "TFUEL": "theta-fuel",
    "THETA": "theta-token",
    "TON": "the-open-network",
    "TRX": "tron",
    "UMEE": "umee",
    "XLM": "stellar",
    "XMR": "monero",
    "XPRT": "persistence",
    "XRP": "ripple",
    "XTZ": "tezos",
    "ZEC": "zcash",
    "ZIL": "zilliqa",
}

network_mappings = {
    "ARBETH": "arbitrum-one",
    "AVAX": "avalanche",
    "BASEETH": "base",
    "BNB": "binance-smart-chain",
    "CELO": "celo",
    "CHZ": "chiliz",
    "ETH": "ethereum",
    "MATIC": "polygon-pos",
    "OETH": "optimistic-ethereum",
    "SOL": "solana",
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


@dataclass
class PlatformInfo:
    decimal_place: int
    contract_address: str

    @classmethod
    def from_dict(cls, dict_: object) -> Self:
        return build_dataclass_from_dict(cls, dict_)


@dataclass
class LinksInfo:
    homepage: [str]
    whitepaper: str

    @classmethod
    def from_dict(cls, dict_: object) -> Self:
        return build_dataclass_from_dict(cls, dict_)


@dataclass
class ImageInfo:
    thumb: str
    small: str
    large: str

    @classmethod
    def from_dict(cls, dict_: object) -> Self:
        return build_dataclass_from_dict(cls, dict_)


@dataclass
class MarketData:
    current_price: dict[str, float]
    market_cap: dict[str, float]
    total_volume: dict[str, float]

    @classmethod
    def from_dict(cls, dict_: object) -> Self:
        return build_dataclass_from_dict(cls, dict_)


@dataclass
class CoinInfo:
    id: str
    symbol: str
    name: str
    platforms: dict[str, str]
    detail_platforms: dict[str, PlatformInfo]
    description: dict[str, str]
    links: LinksInfo
    image: ImageInfo
    market_data: MarketData

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
                f"{CoinGeckoAPIClient.BASE_URL}coins/markets",
                params={
                    'x_cg_pro_api_key': CoinGeckoAPIClient.API_KEY,
                    'vs_currency': 'usd',
                    'ids': ','.join(ids),
                    'per_page': BATCH_SIZE
                }
            ).json()
            return [Market.from_dict(x) for x in response]
        except Exception as e:
            print(f'Error fetching CoinGecko prices: {str(e)}')
            return []

    @staticmethod
    def get_coin_list() -> list[Coin]:
        try:
            response = requests.get(
                f"{CoinGeckoAPIClient.BASE_URL}coins/list",
                params={
                    'x_cg_pro_api_key': CoinGeckoAPIClient.API_KEY,
                    'include_platform': 'true'
                }
            ).json()
            return [Coin.from_dict(x) for x in response]
        except Exception as e:
            print(f'Error fetching CoinGecko coin list: {str(e)}')
            return []

    warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

    @staticmethod
    def get_coin_info(coin_ids: list[str]) -> dict[str, CoinInfo]:
        coin_infos = {}
        for coin_id in coin_ids:
            try:
                response = requests.get(
                    f"{CoinGeckoAPIClient.BASE_URL}coins/{coin_id}",
                    params={
                        'x_cg_pro_api_key': CoinGeckoAPIClient.API_KEY,
                        'localization': 'false',
                        'tickers': 'false',
                        'market_data': 'true',
                        'community_data': 'false',
                        'developer_data': 'false',
                        'sparkline': 'false'
                    }
                ).json()

                coin_infos[coin_id] = CoinInfo.from_dict(response)
            except Exception as e:
                print(f'Error fetching CoinGecko prices: {str(e)}')
                coin_infos[coin_id] = None
        return coin_infos

    @staticmethod
    def get_coin_description(coin_ids: list[str]) -> dict[str, Description]:
        coin_infos = CoinGeckoAPIClient.get_coin_info(coin_ids)
        return {coin_id: Description(
            description=BeautifulSoup(coin_info.description['en'], 'html.parser').get_text(),
            website=coin_info.links.homepage[0]
        ) for coin_id, coin_info in coin_infos.items()}


coin_list = CoinGeckoAPIClient.get_coin_list()
coin_list_by_id = {}
coin_list_by_platform_and_address = {}

for coin in coin_list:
    coin_list_by_id[coin.id] = coin
    for platform, address in coin.platforms.items():
        if address:
            if platform not in coin_list_by_platform_and_address:
                coin_list_by_platform_and_address[platform] = {}
            coin_list_by_platform_and_address[platform][address.lower()] = coin


def get_coin_by_id(coin_symbol):
    coin_gecko_id = coin_mappings.get(coin_symbol)
    if coin_gecko_id is None:
        return None
    return coin_list_by_id.get(coin_gecko_id, None)


def get_coin_by_chain_and_address(chain, token_address):
    network_id = network_mappings.get(chain, None)
    if network_id is None:
        return None
    return coin_list_by_platform_and_address.get(network_id, {}).get(token_address.lower(), None)


def get_coins_by_id(coins):
    coins_by_id = {}
    for coin in coins:
        coin_gecko_id = coin_mappings.get(coin.symbol)
        if coin_gecko_id is not None:
            coins_by_id.setdefault(coin_gecko_id, []).append(coin)
    return coins_by_id


def get_tokens_by_id(network, tokens):
    tokens_by_id = {}
    network_coin_gecko_id = network_mappings.get(network.symbol)
    if network_coin_gecko_id is not None:
        for token in tokens:
            coin = coin_list_by_platform_and_address.get(network_coin_gecko_id, {}).get(token.address.lower(), None)
            if coin is not None:
                tokens_by_id.setdefault(coin.id, []).append(token)
    return tokens_by_id


def fetch_coin_prices(coins):
    coins_by_id = get_coins_by_id(coins)
    prices = {}
    for batch in map_chunked(CoinGeckoAPIClient.fetch_usd_markets, list(coins_by_id.keys()), BATCH_SIZE):
        for market in batch:
            for coin in coins_by_id.get(market.id):
                prices[coin.symbol] = market.current_price
    return prices


def fetch_token_prices(network, tokens):
    tokens_by_id = get_tokens_by_id(network, tokens)
    prices = {}
    for batch in map_chunked(CoinGeckoAPIClient.fetch_usd_markets, list(tokens_by_id.keys()), BATCH_SIZE):
        for market in batch:
            for token in tokens_by_id[market.id]:
                prices[token.with_suffix(network).symbol] = market.current_price
    return prices


def fetch_coin_descriptions(coins):
    coins_by_id = get_coins_by_id(coins)
    descriptions = {}
    for id, description in map_chunked(CoinGeckoAPIClient.get_coin_description, list(coins_by_id.keys()), 1):
        if description is not None:
            for coin in coins_by_id[id]:
                descriptions[coin.symbol] = description
    return descriptions


def fetch_token_descriptions(network, tokens):
    tokens_by_id = get_tokens_by_id(network, tokens)
    descriptions = {}
    for id, description in map_chunked(CoinGeckoAPIClient.get_coin_description, list(tokens_by_id.keys()), 1):
        if description is not None:
            for token in tokens_by_id[id]:
                descriptions[token.symbol] = description
    return descriptions


def fetch_missing_tokens_for_network(network, tokens):
    existing_coin_ids = get_tokens_by_id(network, tokens).keys()
    coingecko_platform = network_mappings.get(network.symbol)
    if (coingecko_platform is None):
        return []
    network_coin_ids = []
    for coin in coin_list:
        if coingecko_platform in coin.platforms and coin.id not in existing_coin_ids:
            network_coin_ids.append(coin.id)
    print(f"Found {str(len(network_coin_ids))} missing coins in CoinGecko for {network.symbol}")
    new_tokens = []
    for coin_infos in map_chunked(CoinGeckoAPIClient.get_coin_info, network_coin_ids, 10):
        for (coin_id, coin_info) in coin_infos.items():
            if coin_info is None:
                # print(f"Got None coin_info for {coin_id}")
                continue
            usd_24h_volume = coin_info.market_data.total_volume.get('usd', 0)
            usd_mkcap = coin_info.market_data.market_cap.get('usd', 0)
            if usd_24h_volume < 250_000 and usd_mkcap < 25_000_000:
                # print(f"Skipping {coin_id} due to low USD volume ({usd_24h_volume}) and market cap ({usd_mkcap})")
                continue
            # print(f"Adding {coin_id} (volume={usd_24h_volume}, mkcap={usd_mkcap})")
            address = coin_info.detail_platforms[coingecko_platform].contract_address
            if Web3.is_address(address):
                address = Web3.to_checksum_address(address)
            new_tokens.append(Token(
                address=address,
                decimals=coin_info.detail_platforms[coingecko_platform].decimal_place,
                displaySymbol=coin_info.symbol.upper(),
                logo=coin_info.image.large,
                name=coin_info.name,
                symbol=coin_info.symbol.upper(),
                website=coin_info.links.homepage[0]
            ))
    return new_tokens
