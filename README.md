# Inventory CLI

A Python command-line inventory tool for a small store. Track prices and quantities,
then use `low-stock` to find items that need replenishing. Each invocation performs
one operation and exits. Duplicate product names are allowed.

## Run

Requires Python 3.9 or newer. No packages need installing. From this directory:

```sh
python3 products.py --help
python3 products.py add --name "Notebook" --price 4.5 --quantity 10
python3 products.py list
python3 products.py get 1
python3 products.py update 1 --quantity 12
python3 products.py delete 1 --yes
```

Full syntax:

```text
python3 products.py [--file PATH] add --name NAME --price PRICE --quantity QTY
python3 products.py [--file PATH] list
python3 products.py [--file PATH] get ID
python3 products.py [--file PATH] update ID [--name NAME] [--price PRICE] [--quantity QTY]
python3 products.py [--file PATH] delete ID --yes
python3 products.py [--file PATH] low-stock --threshold QTY
```

Update requires at least one field. Delete requires explicit `--yes`, without a
prompt. Use `python3 products.py COMMAND --help` for help on any command.

The default file is `products.json` in the process working directory, which can
be different from the script directory. `--file` must precede the command.
Relative paths resolve from the process working directory. Quote paths with spaces:

```sh
python3 products.py --file "demo.json" add --name "Pencil" --price 1.25 --quantity 5
python3 products.py --file "demo.json" list
```

For another filename, use e.g. `--file "shop inventory.json"`. Parent directories
must already exist. Add custom local inventory filenames to `.gitignore` before
staging files; only the default and demo filenames are ignored automatically.

## Low-stock replenishment report

Store owners can review stock at or below a chosen reorder threshold. This helps
identify purchases before shelves become empty. The required `--threshold` takes
nonnegative ASCII digits, including zero. Results are sorted by numeric ID.
With the fresh demo file created above:

```sh
python3 products.py --file demo.json low-stock --threshold 5
```

Expected JSON:

```json
[{"id": 1, "name": "Pencil", "price": "1.25", "quantity": 5}]
```

Edge case (no matching products):

```sh
python3 products.py --file demo.json low-stock --threshold 0
```

Expected output: `[]`. A missing store also returns `[]` without creating a file.
The boundary is inclusive; zero threshold finds zero-quantity items.

## Data and validation

After the first Notebook add, the UTF-8 JSON store is:

```json
{
  "next_id": 2,
  "products": [
    {"id": 1, "name": "Notebook", "price": "4.50", "quantity": 10}
  ]
}
```

The top-level keys and the four product fields are exact. IDs are positive integers,
start at 1, remain stable during updates, and are never reused after deletion.
`next_id` persists independently of existing IDs. Gaps and unsorted stored records
are valid. Booleans are not accepted as integers.

Names are trimmed at both ends; interior spacing and Unicode text are preserved.
Blank names are rejected. Prices accept ASCII digits optionally followed by a dot
and one or two digits: `0`, `4`, `4.5`, `0004.50`. Exact string normalization produces
`0.00`, `4.00`, `4.50`, `4.50`, without floating-point rounding. Signs, exponents,
currency symbols, spaces, Unicode digits and trailing dots are rejected. Quantities
are nonnegative ASCII-digit integers; command IDs use the same syntax but must be
positive. No arbitrary numeric or product-count limits are imposed.

Every operation reads and validates the entire existing store. Invalid JSON,
invalid UTF-8, empty existing files, duplicate JSON keys, extra schema fields,
untrimmed names, duplicate IDs, noncanonical stored prices, and inconsistent
`next_id` are errors. Stored prices use no redundant leading zeroes. Missing files
represent an empty inventory; read-only commands do not create or rewrite them.

Mutations follow parse/validate, read/validate, modify, serialize, write temporary
file in the same directory, flush and sync, then `os.replace`. Success is printed
only after saving. Failed writes clean up their temporary files. Read-only commands
are `list`, `get`, and `low-stock`. Output is one JSON value; Unicode escapes keep
JSON portable and preserve original text when decoded. Concurrent writers are not
coordinated; use one writing process at a time.

## Exit codes

| Code | Meaning | Example |
| --- | --- | --- |
| 0 | Success or help | `python3 products.py list` |
| 1 | Missing product, invalid store, or filesystem error | `python3 products.py get 999999` (when absent) |
| 2 | Syntax or supplied input error | `python3 products.py add --name X --price 1.234 --quantity 1` |

Errors go to stderr, without success JSON or expected-error tracebacks. Invalid
operations preserve the existing file and do not consume IDs.

## Tests and development

```sh
python3 -m unittest discover -s tests -v
```

The suite uses `unittest`, `tempfile`, subprocesses and `unittest.mock`. It isolates
all inventories in temporary directories and executes the instructor sequence,
CRUD, malformed CLI and schema cases, low-stock boundaries, alternate paths,
read-only integrity, very large values, and injected filesystem failures. Injected
permission failures are deterministic and do not depend on the test user's access.

Development used Codex, a shell, Python's standard library, and Git. There are no
third-party runtime or test dependencies. Agent-identification comments are present
in the implementation as requested. See `SUBMISSION.md` for executed verification,
rubric limitations, recording commands, and publication steps.

## License

MIT; see `LICENSE`.
