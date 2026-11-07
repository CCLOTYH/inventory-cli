# Submission readiness

## Executed verification

`python3 -m unittest discover -s tests -v`: **19 tests passed, 0 failures**.
The initial run used the equivalent workspace-relative tests directory. Tests use
many subcases; 19 is the unittest method count, not a claim about rubric points.
The exact instructor command sequence was executed in an isolated temporary
working directory by `test_instructor_sequence`. It verified the final Notebook,
quantity 12, price 4.50, retained next_id 3, and subsequent ID 3.

No failing tests were encountered. Contract review proactively addressed Python's
integer digit limit, exact price normalization, argparse flag abbreviation,
boolean integer fields, duplicate JSON keys, and atomic-save cleanup. These are
implementation decisions, not claims of failures observed and repaired.

Verified behavior includes all six commands, strict CLI input and loaded-schema
validation, persistence, stable IDs, JSON output, error codes, alternate paths,
read-only integrity, and atomic write failure handling. No handout or published
rubric was present in the supplied workspace. The fallback requirements were used.
Extra top-level fields and redundant leading zeros in stored prices are rejected
based on the requested exact schema and canonical formatting. Leading zeros in
price input are accepted and normalized. No concurrency guarantee is claimed.

## Rubric audit

Without the published criterion text, assigning numbered criteria to implemented
features would invent a mapping. The statuses below therefore distinguish direct
contract verification above from unverified rubric attribution.

| Criterion | Status | Evidence / limitation |
| --- | --- | --- |
| A1-01 | Not yet verified | Published criterion definition unavailable |
| A1-02 | Not yet verified | Published criterion definition unavailable |
| A1-03 | Not yet verified | Published criterion definition unavailable |
| A1-04 | Not yet verified | Published criterion definition unavailable |
| A1-05 | Not yet verified | Published criterion definition unavailable |
| A1-06 | Not yet verified | Published criterion definition unavailable |
| A1-07 | Not yet verified | Published criterion definition unavailable |
| A1-08 | Not yet verified | Published criterion definition unavailable |
| A1-09 | Not yet verified | Published criterion definition unavailable |
| A1-10 | Not yet verified | Published criterion definition unavailable |
| A1-11 | Not yet verified | Published criterion definition unavailable |
| A1-12 | Not yet verified | Published criterion definition unavailable |
| A1-13 | Not yet verified | Published criterion definition unavailable |
| A1-14 | Requires video evidence | User identifies this as recording-dependent; no recording made |
| A1-15 | Requires video evidence | User identifies this as recording-dependent; no recording made |
| A1-16 | Requires video evidence | User identifies this as recording-dependent; no recording made |

No score is claimed. Before submission, compare this project with the actual rubric
version 1.0.0 and record any required evidence personally.

## Recording plan (commands to execute later, not a transcript)

From the project directory, create an isolated demonstration directory so existing
inventory is preserved:

```sh
PROJECT="$PWD"
DEMO_DIR="$(mktemp -d)"
cd "$DEMO_DIR"
python3 "$PROJECT/products.py" --help
python3 "$PROJECT/products.py" add --name "Notebook" --price 4.5 --quantity 10
python3 "$PROJECT/products.py" add --name "Pencil" --price 1.25 --quantity 5
python3 "$PROJECT/products.py" list
python3 "$PROJECT/products.py" get 1
python3 "$PROJECT/products.py" update 1 --quantity 12
python3 "$PROJECT/products.py" delete 2 --yes
python3 "$PROJECT/products.py" list
cat products.json
python3 "$PROJECT/products.py" add --name "Eraser" --price 0 --quantity 0
python3 "$PROJECT/products.py" low-stock --threshold 12
python3 "$PROJECT/products.py" low-stock --threshold 0
python3 "$PROJECT/products.py" --file "separate store.json" low-stock --threshold 0
```

The saved counter after deletion is 3. Eraser receives ID 3. Threshold 12 includes
Notebook and Eraser; threshold 0 includes only Eraser. The separate missing store
returns an empty array without creating it.

Demonstrate failures and exit codes (each `echo` immediately follows its command):

```sh
python3 "$PROJECT/products.py" add --name "Invalid" --price 1.234 --quantity 1
echo $?
python3 "$PROJECT/products.py" update 1 --quantity -1
echo $?
python3 "$PROJECT/products.py" delete 1
echo $?
python3 "$PROJECT/products.py" get 999
echo $?
python3 "$PROJECT/products.py" low-stock --threshold -1
echo $?
python3 "$PROJECT/products.py" list
cd "$PROJECT"
python3 -m unittest discover -s tests -v
git log -1 --format=%H
git status --short
```

Expected failure codes in order: 2, 2, 2, 1, 2. The final inventory is unchanged by
these failures. Show the source, README, custom feature rationale, test results,
and eventual public repository as required by the actual recording instructions.

## GitHub publication and remaining steps

The public GitHub repository was created at:
https://github.com/CCLOTYH/inventory-cli

The GitHub page explicitly labels the repository Public. Local Git has this URL
configured as origin. Command-line push could not authenticate, so publication
uses the signed-in GitHub web upload interface. Web uploads create their own
commits; the original local implementation commit is retained separately:
`a0f7fd84c22a0891bfe6fb7ecfff0144c1ec208a`.

For future development, clone the published repository to a fresh directory so
its web-created history is the starting point:

```sh
git clone https://github.com/CCLOTYH/inventory-cli.git
cd inventory-cli
python3 -m unittest discover -s tests -v
```

Authenticate Git or GitHub CLI before future pushes. Do not force-push the original
local history over the web-created history. Then review the actual handout, make
the required recording, and submit the repository/recording links through the
course portal yourself. No recording or course portal submission has been made.
