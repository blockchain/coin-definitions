# Skill: Generate SQL Category Files for Ondo Tokens

## Trigger

Use this skill when the user wants to generate SQL insert files for Ondo token categories and sub-categories from an Excel spreadsheet.

---

## Step 0 — Ask for inputs

If not already provided, ask:
1. **Excel file path** — full path to the `.xlsx` file
---

## Step 1 — Read the Excel sheet

Use Python with `openpyxl` via a venv if not available system-wide:

```bash
python3 -m venv /tmp/xlvenv && /tmp/xlvenv/bin/pip install openpyxl -q
```

Read with `data_only=True` to resolve formula cells:

```python
import openpyxl
wb = openpyxl.load_workbook('<path>', data_only=True)
ws = wb.active
```

**Required columns (0-indexed):**

| Index | Field |
|-------|-------|
| 1 | Symbol (mixed-case, e.g. `GLWon`) |
| 20 | Type (`Stock`, `ETF`, `CEF`) |
| 21 | Sector - Industry Group |

Skip rows where `row[0]` is empty.

---

## Step 2 — Map sub_category

Available sub_categories from `assets.sub_category`:

```
TECH | FINANCE | HEALTH | CONSUMER | ENERGY | MEDIA | CRYPTO | ETF | COMMODITIES | CURRENCY | AEROSPACE
```

### Mapping rules (apply in order):

**1. ETF/CEF type → always `ETF`**

**2. Manual overrides by symbol** (companies whose sector label doesn't reflect their business):

| Symbol | Sub-category | Reason |
|--------|-------------|--------|
| `BEON` | `ENERGY` | Bloom Energy — clean energy |
| `SMRON` | `ENERGY` | NuScale Power — nuclear energy |
| `NNEON` | `ENERGY` | NANO Nuclear Energy |
| `GNRCON` | `ENERGY` | Generac — power generation |
| `FPSON` | `ENERGY` | Forgent Power Solutions |
| `FLNCON` | `ENERGY` | Fluence Energy |
| `FCELON` | `ENERGY` | FuelCell Energy |
| `AAONON` | `CONSUMER` | AAON — commercial HVAC |

**3. Sector-based mapping:**

| Sector contains | Sub-category |
|----------------|-------------|
| `TECHNOLOGY`, `SOFTWARE`, `IT SERVICES`, `SEMICONDUCTORS` | `TECH` |
| `AEROSPACE`, `DEFENSE` | `AEROSPACE` |
| `ENERGY`, `OIL`, `GAS`, `RENEWABLE` | `ENERGY` |
| `TRANSPORTATION` | `ENERGY` (oil tankers) |
| `ENGINEERING`, `CONSTRUCTION` | `ENERGY` (energy infrastructure contractors) |
| `STEEL`, or `MATERIALS` + (`MINING`, `METAL`, `CHEMICAL`) | `COMMODITIES` |
| `FINANCIAL`, `FINANCE`, `ASSET MANAGEMENT`, `SPECIALTY FINANCE` | `FINANCE` |
| `CONSUMER`, `AUTOMOTIVE` | `CONSUMER` |
| `TELECOMMUNICATIONS`, `INTERNET MEDIA`, `COMMUNICATIONS` | `MEDIA` |
| `INDUSTRIALS` (all remaining) | `TECH` |

**Fallback:** `TECH`

---

## Step 3 — Generate SQL files

Create three files in the `sql/` directory at the repo root. The `sql/` folder is gitignored — do not stage or commit it.

**File naming:** `sql/<branch_prefix>-ondo-eth.sql`, `sql/<branch_prefix>-ondo-bnb.sql`, `sql/<branch_prefix>-ondo-sol.sql`

Where `<branch_prefix>` is derived automatically from the current git branch:

```bash
git rev-parse --abbrev-ref HEAD
```


**Currency key format:**

| File | Currency key |
|------|-------------|
| ETH | `SYMBOL` (no suffix) |
| BNB | `SYMBOL.BNB` |
| SOL | `SYMBOL.SOL` |

**SQL structure for each file:**

```sql
BEGIN;
  INSERT INTO assets.currency_category(id, currency, category)
    VALUES ('<uuid4>', '<CURRENCY>', 'STOCK'),
      ('<uuid4>', '<CURRENCY>', 'STOCK'),
      ...;

  INSERT INTO assets.currency_sub_category (id, currency, sub_category)
    VALUES ('<uuid4>', '<CURRENCY>', '<SUB_CATEGORY>'),
      ('<uuid4>', '<CURRENCY>', '<SUB_CATEGORY>'),
      ...;
COMMIT;
```

**Key rules:**
- `category` is always `'STOCK'` for every token regardless of type (ETFs included)
- Every token gets both a category and a sub_category row
- Generate a fresh `uuid.uuid4()` for every row — each UUID is unique across all inserts
- `SYMBOL` is always uppercase (`str(row[1]).upper()`)

**Python generation pattern:**

```python
import uuid

def build_sql(tokens, suffix):
    cat_rows = []
    sub_rows = []
    for t in tokens:
        currency = t['symbol'] + suffix
        cat_rows.append(f"      ('{uuid.uuid4()}', '{currency}', 'STOCK')")
        sub_rows.append(f"      ('{uuid.uuid4()}', '{currency}', '{t['sub_category']}')")

    lines = ['BEGIN;']
    lines.append('  INSERT INTO assets.currency_category(id, currency, category)')
    lines.append('    VALUES ' + ',\n'.join(cat_rows) + ';')
    lines.append('')
    lines.append('  INSERT INTO assets.currency_sub_category (id, currency, sub_category)')
    lines.append('    VALUES ' + ',\n'.join(sub_rows) + ';')
    lines.append('COMMIT;')
    return '\n'.join(lines) + '\n'
```

---

## Step 4 — Verify before handing off

Print a summary of the sub_category distribution so the user can confirm the mappings are correct before running the SQL:

```
Sub-category distribution:
  TECH: 78
  ETF: 43
  ENERGY: 22
  COMMODITIES: 12
  FINANCE: 8
  CONSUMER: 4
  AEROSPACE: 3
  MEDIA: 3
```

Also list any tokens whose mapping might be non-obvious (manual overrides, Industrials assigned to non-TECH, etc.) so the user can review them.

---

## Notes

- The `sql/` directory is gitignored — these files are for local DB seeding only, never committed
- `category` is always `STOCK` even for ETF/CEF tokens — the `sub_category` table is what distinguishes them
- All four UUIDs per token (2 per file × 3 files for ETH+BNB+SOL) must be distinct
- If the user only needs a subset of chains, generate only the requested files
- Follow the exact format of existing reference files: `devx/add-third-ondo-eth.sql` and `devx/add-third-ondo-bnb.sql`
