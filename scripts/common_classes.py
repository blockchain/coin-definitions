import os
import re
from dataclasses import dataclass, replace, fields
from urllib.parse import urljoin

from statics import BC_REPO_ROOT, EXT_BLOCKCHAINS, BLOCKCHAINS, TW_REPO_ROOT


def build_dataclass_from_dict(cls, dict_):
    class_fields = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in dict_.items() if k in class_fields})


@dataclass
class Asset:
    id: str
    decimals: int
    name: str
    symbol: str
    website: str
    status: str
    displaySymbol: str = None

    @classmethod
    def from_dict(cls, dict_):
        return build_dataclass_from_dict(cls, dict_)


@dataclass
class Blockchain:
    name: str
    key: str
    symbol: str = None
    decimals: int = None
    status: str = None
    website: str = None

    def is_valid(self):
        return self.symbol is not None and \
            self.decimals is not None and \
            self.status is not None

    def is_active(self):
        return self.status == 'active'

    def is_removed(self):
        return self.status == 'removed'

    @classmethod
    def from_dict(cls, key, dict_):
        dict_ = dict(dict_.items())
        dict_.update(dict(key=key))
        return build_dataclass_from_dict(cls, dict_)


@dataclass
class Coin:
    symbol: str
    name: str
    key: str
    decimals: int
    logo: str
    website: str

    @staticmethod
    def build_currency_logo(key):
        if os.path.exists(os.path.join(EXT_BLOCKCHAINS, key, "info", "logo.png")):
            return BC_REPO_ROOT + os.path.join(EXT_BLOCKCHAINS, key, "info", "logo.png")
        elif os.path.exists(os.path.join(BLOCKCHAINS, key, "info", "logo.png")):
            return TW_REPO_ROOT + os.path.join("blockchains", key, "info", "logo.png")
        else:
            return None

    @staticmethod
    def from_chain(chain):
        return Coin(
            symbol=chain.symbol,
            name=chain.name,
            key=chain.key,
            logo=Coin.build_currency_logo(chain.key),
            decimals=chain.decimals,
            website=chain.website
        )

    @classmethod
    def from_dict(cls, dict_):
        return build_dataclass_from_dict(cls, dict_)


@dataclass
class Description:
    description: str
    website: str


@dataclass
class Token:
    address: str
    decimals: int
    displaySymbol: str
    logo: str
    name: str
    symbol: str
    website: str

    def is_valid(self):
        # At most 8 letters and digits:
        return re.match("^[a-zA-Z0-9]{1,8}$", self.symbol) is not None

    @staticmethod
    def build_token_logo(address, chain):
        if os.path.exists(os.path.join(f"extensions/blockchains/{chain}/assets/", address, "logo.png")):
            base_path = BC_REPO_ROOT + f"extensions/blockchains/{chain}/assets/"
        else:
            base_path = TW_REPO_ROOT + f"blockchains/{chain}/assets/"
        asset_path = urljoin(base_path, address + "/")
        return urljoin(asset_path, "logo.png")

    @staticmethod
    def from_asset(asset, chain):
        return Token(
            address=asset.id,
            decimals=asset.decimals,
            displaySymbol=asset.displaySymbol or asset.symbol,
            logo=Token.build_token_logo(asset.id, chain),
            name=asset.name,
            symbol=asset.symbol,
            website=asset.website
        )

    def should_append_network_suffix(self, network):
        if network.symbol == "ETH":
            return False
        # TODO: Remove special case for CEUR and CUSD (CTP-332)
        if network.symbol == "CELO" and (self.symbol == "CEUR" or self.symbol == "CUSD"):
            return False
        return True

    def with_suffix(self, network):
        if self.should_append_network_suffix(network):
            return replace(self, symbol=f"{self.symbol}.{network.symbol}")
        return self

    def without_suffix(self, network):
        return replace(self, symbol=self.symbol.removesuffix(f".{network.symbol}"))

    @classmethod
    def from_dict(cls, dict_):
        return build_dataclass_from_dict(cls, dict_)

    def __eq__(self, other):
        return self.address == other.address

    def __hash__(self):
        return hash(self.address)
