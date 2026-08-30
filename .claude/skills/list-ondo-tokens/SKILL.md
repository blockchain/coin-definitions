# Skill: List Ondo Tokens from Excel Sheet

## Trigger

Use this skill when the user wants to add Ondo tokenized assets from an Excel spreadsheet into the coin-definitions repository.

---

## Step 0 — Ask for the Excel path

If the user hasn't provided the path to the Excel file, ask:

> "What is the full path to the Excel file?"

---

## Step 1 — Read the Excel sheet

Use Python with `openpyxl` (install via a venv if not available system-wide):

```bash
python3 -m venv /tmp/xlvenv && /tmp/xlvenv/bin/pip install openpyxl -q
```

Read with `data_only=True` to resolve formula cells:

```python
import openpyxl
wb = openpyxl.load_workbook('<path>', data_only=True)
ws = wb.active
```

**Expected columns (0-indexed):**

| Index | Field |
|-------|-------|
| 0 | Name |
| 1 | Symbol (mixed-case displaySymbol, e.g. `GLWon`) |
| 4 | Ethereum deployed address |
| 5 | BSC (Smartchain) deployed address |
| 6 | Solana deployed address |
| 16 | Logo PNG URL |
| 23 | Description |

Skip rows where `row[0]` is empty.

---

## Step 2 — Create token folders and info.json

Base path: `extensions/blockchains/`

For each token, create a folder per chain where an address exists. Skip chains with no address.

### Folder naming

- **Ethereum** and **Smartchain**: lowercase the address
- **Solana**: preserve original casing

### info.json format

**Ethereum** (`extensions/blockchains/ethereum/assets/<lowercase_addr>/info.json`):
```json
{
  "name": "<name without any suffix>",
  "website": "https://ondo.finance/",
  "type": "ERC20",
  "symbol": "<SYMBOL_UPPERCASE>",
  "decimals": 18,
  "status": "active",
  "id": "<lowercase_address>"
}
```

**Smartchain** (`extensions/blockchains/smartchain/assets/<lowercase_addr>/info.json`):
```json
{
  "id": "<lowercase_address>",
  "name": "<name without any suffix>",
  "symbol": "<SYMBOL_UPPERCASE>",
  "type": "BEP20",
  "decimals": 18,
  "status": "active",
  "website": "https://ondo.finance/",
  "displaySymbol": "<symbol_as_in_excel>"
}
```

**Solana** (`extensions/blockchains/solana/assets/<original_addr>/info.json`):
```json
{
  "displaySymbol": "<symbol_as_in_excel>",
  "symbol": "<SYMBOL_UPPERCASE>",
  "name": "<name without any suffix>",
  "id": "<original_address>",
  "type": "SOLANA_TOKEN",
  "decimals": 6,
  "status": "active",
  "website": "https://ondo.finance"
}
```

**Key rules:**
- `name`: strip `" (Ondo Tokenized)"` or any parenthetical suffix — use the clean name only
- `symbol`: always uppercase (`str(row[1]).upper()`)
- `displaySymbol`: taken directly from column 1 as-is (e.g. `GLWon`)

### Logo

Download `logo.png` from column 16 URL into each chain folder:

```python
import urllib.request
urllib.request.urlretrieve(logo_url, os.path.join(folder, "logo.png"))
```

---

## Step 3 — Run the build script

```bash
python3 scripts/build-lists.py --ci
```

Ensure dependencies are installed (`requests`, `bs4`, `web3`, `bech32`) — check `requirements.txt` and install with `pip3 install -r requirements.txt --break-system-packages -q` if needed.

---

## Step 4 — Add descriptions to extensions/overrides.json

Read `extensions/overrides.json`, then for each token add **three keys** to the `descriptions` object:

| Key | Chain |
|-----|-------|
| `<SYMBOL_UPPERCASE>` | Ethereum |
| `<SYMBOL_UPPERCASE>.BNB` | Smartchain / Binance |
| `<SYMBOL_UPPERCASE>.SOL` | Solana |

All three keys share the same description string (column 23 from Excel).

Only add keys that don't already exist. Write back with `json.dump(overrides, f, indent=2)` followed by a trailing newline.

---

## Step 5 — Run the descriptions fill script

```bash
python3 scripts/build-lists.py --fill-descriptions-from-overrides
```

This updates `description/en.json` and `description/info.json`.

---

## Step 6 — Git staging (critical — be selective)

Stage **only** changes related to the tokens in the Excel sheet. The build scripts touch many chains; only stage what belongs to this work.

### Stage new token asset files

```bash
git status --short | grep "^A " | awk '{print $2}' | xargs git add
```

This picks up only newly added files (`A` status). Do **not** stage `M` (modified) files inside `extensions/blockchains/` — those belong to pre-existing tokens that were not part of this Excel sheet.

### Stage relevant build outputs

```bash
git add erc20-tokens.json chain/binance/tokens.json chain/solana/tokens.json
```

Do **not** stage unrelated chain outputs such as `chain/tron/tokens.json`, `chain/celo/tokens.json`, `chain/base/tokens.json`, etc.

### Stage overrides and description files

```bash
git add extensions/overrides.json description/en.json description/info.json
```

### Unstage any pre-existing modified tokens that crept in

```bash
git status --short | grep "^M " | grep "extensions/blockchains" | awk '{print $2}' | xargs git restore --staged
```

### Final check

Verify the staged set looks correct:
- `A` files: `extensions/blockchains/{ethereum,smartchain,solana}/assets/*/info.json` and `logo.png` — one pair per token per chain
- `M` files: `erc20-tokens.json`, `chain/binance/tokens.json`, `chain/solana/tokens.json`, `extensions/overrides.json`, `description/en.json`, `description/info.json`
- No `M` files under `extensions/blockchains/` (those are pre-existing tokens)

---

## Notes

- **Binance = smartchain** folder, `BEP20` type, `.BNB` description key
- **Solana = solana** folder, `SOLANA_TOKEN` type, `.SOL` description key
- **Ethereum = ethereum** folder, `ERC20` type, no chain suffix on description key
- If a token already has a folder, skip it (use `os.path.exists` before `os.makedirs`)
- The Excel `Symbol` column is the mixed-case `displaySymbol`; uppercase it for the `symbol` field
