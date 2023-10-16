from dataclasses import dataclass

TW_REPO_ROOT = "https://raw.githubusercontent.com/trustwallet/assets/master/"
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
    output_file: str
    explorer_url: str


ERC20_NETWORKS = [
    ERC20Network(
        chain="ethereum",
        symbol="ETH",
        output_file="erc20-tokens.json",
        explorer_url="https://etherscan.io/token/"
    ),
    ERC20Network(
        chain="polygon",
        symbol="MATIC",
        output_file="chain/polygon/tokens.json",
        explorer_url="https://polygonscan.com/token/"
    ),
    ERC20Network(
        chain="tron",
        symbol="TRX",
        output_file="chain/tron/tokens.json",
        explorer_url="https://tronscan.org/#/token20/"
    ),
    ERC20Network(
        chain="arbitrum",
        symbol="ARBETH",
        output_file="chain/arbitrum/tokens.json",
        explorer_url="https://arbiscan.io/token/"
    ),
    ERC20Network(
        chain="chiliz",
        symbol="CHZ",
        output_file="chain/chiliz/tokens.json",
        explorer_url="https://explorer.chiliz.com/address/"
    ),
    ERC20Network(
        chain="celo",
        symbol="CELO",
        output_file="chain/celo/tokens.json",
        explorer_url="https://celoscan.io/token/"
    ),
    ERC20Network(
        chain="avalanchec",
        symbol="AVAX",
        output_file="chain/avalanchec/tokens.json",
        explorer_url="https://snowtrace.io/token/"
    ),
    ERC20Network(
        chain="optimism",
        symbol="OETH",
        output_file="chain/optimism/tokens.json",
        explorer_url="https://optimistic.etherscan.io/token/"
    )
]
