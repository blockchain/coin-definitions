from dataclasses import dataclass

TW_REPO_ROOT = "https://raw.githubusercontent.com/trustwallet/assets/37dd998/"
BC_REPO_ROOT = "https://raw.githubusercontent.com/blockchain/coin-definitions/master/"

BLOCKCHAINS = "assets/blockchains/"

EXT_BLOCKCHAINS = "extensions/blockchains/"
EXT_BLOCKCHAINS_DENYLIST = "extensions/blockchains/denylist.txt"

EXT_PRICES = "extensions/prices.json"

FINAL_BLOCKCHAINS_LIST = "coins.json"


@dataclass
class ERC20Network:
    chain: str
    symbol: str
    assets_dir: str
    ext_assets_dir: str
    denylist: str
    output_file: str
    symbol_suffix: str
    explorer_url: str


ERC20_NETWORKS = [
    ERC20Network(
        chain="ethereum",
        symbol="ETH",
        assets_dir="assets/blockchains/ethereum/assets/",
        ext_assets_dir="extensions/blockchains/ethereum/assets/",
        denylist="extensions/blockchains/ethereum/denylist.txt",
        output_file="erc20-tokens.json",
        symbol_suffix="",
        explorer_url="https://etherscan.io/token/"
    ),
    ERC20Network(
        chain="polygon",
        symbol="MATIC",
        assets_dir="assets/blockchains/polygon/assets/",
        ext_assets_dir="extensions/blockchains/polygon/assets/",
        denylist="extensions/blockchains/polygon/denylist.txt",
        output_file="chain/polygon/tokens.json",
        symbol_suffix="MATIC",
        explorer_url="https://polygonscan.com/token/"
    ),
    ERC20Network(
        chain="binance",
        symbol="BNB",
        assets_dir="assets/blockchains/smartchain/assets/",
        ext_assets_dir="extensions/blockchains/smartchain/assets/",
        denylist="extensions/blockchains/binance/denylist.txt",
        output_file="chain/binance/tokens.json",
        symbol_suffix="BNB",
        explorer_url="https://bscscan.com/token/"
    ),
    ERC20Network(
        chain="tron",
        symbol="TRX",
        assets_dir="assets/blockchains/tron/assets/",
        ext_assets_dir="extensions/blockchains/tron/assets/",
        denylist="extensions/blockchains/tron/denylist.txt",
        output_file="chain/tron/tokens.json",
        symbol_suffix="TRX",
        explorer_url="https://tronscan.org/#/token20/"
    ),
    ERC20Network(
        chain="arbitrum",
        symbol="ARBETH",
        assets_dir="assets/blockchains/arbitrum/assets/",
        ext_assets_dir="extensions/blockchains/arbitrum/assets/",
        denylist="extensions/blockchains/arbitrum/denylist.txt",
        output_file="chain/arbitrum/tokens.json",
        symbol_suffix="ARBETH",
        explorer_url="https://arbiscan.io/token/"
    ),
    ERC20Network(
        chain="chiliz",
        symbol="CHZ",
        assets_dir="assets/blockchains/chiliz/assets/",
        ext_assets_dir="extensions/blockchains/chiliz/assets/",
        denylist="extensions/blockchains/chiliz/denylist.txt",
        output_file="chain/chiliz/tokens.json",
        symbol_suffix="CHZ",
        explorer_url="https://explorer.chiliz.com/address/"
    ),
    ERC20Network(
        chain="celo",
        symbol="CELO",
        assets_dir="assets/blockchains/celo/assets/",
        ext_assets_dir="extensions/blockchains/celo/assets/",
        denylist="extensions/blockchains/celo/denylist.txt",
        output_file="chain/celo/tokens.json",
        symbol_suffix="CELO",
        explorer_url="https://celoscan.io/token/"
    ),
    ERC20Network(
        chain="avalanche",
        symbol="AVAX",
        assets_dir="assets/blockchains/avalanchec/assets/",
        ext_assets_dir="extensions/blockchains/avalanchec/assets/",
        denylist="extensions/blockchains/avalanchec/denylist.txt",
        output_file="chain/avalanchec/tokens.json",
        symbol_suffix="AVAX",
        explorer_url="https://snowtrace.io/token/"
    ),
    ERC20Network(
        chain="optimism",
        symbol="OP",
        assets_dir="assets/blockchains/optimism/assets/",
        ext_assets_dir="extensions/blockchains/optimism/assets/",
        denylist="extensions/blockchains/optimism/denylist.txt",
        output_file="chain/optimism/tokens.json",
        symbol_suffix="OP",
        explorer_url="https://optimistic.etherscan.io/token/"
    )
]
