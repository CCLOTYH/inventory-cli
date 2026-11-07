#!/usr/bin/env python3
"""Noninteractive inventory CLI; Python standard library only."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile

# CODING_AGENT_IDENTIFIED_FLAG: avoid interpreter digit limits on valid integers.
if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)


class StoreError(Exception):
    """An expected storage or missing-product error."""


# CODING_AGENT_IDENTIFIED_FLAG: validate input before loading or mutating data.
def natural(value):
    if not re.fullmatch(r"[0-9]+", value):
        raise argparse.ArgumentTypeError("must contain only ASCII digits")
    return int(value)


def identifier(value):
    result = natural(value)
    if result == 0:
        raise argparse.ArgumentTypeError("ID must be positive")
    return result


def name_value(value):
    value = value.strip()
    if not value:
        raise argparse.ArgumentTypeError("name must contain non-whitespace text")
    return value


def price_value(value):
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", value):
        raise argparse.ArgumentTypeError("price must be ASCII digits with optional 1 or 2 decimal digits")
    whole, _, fraction = value.partition(".")
    return (whole.lstrip("0") or "0") + "." + fraction.ljust(2, "0")


def parser():
    root = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    root.add_argument("--file", default="products.json", help="JSON path (before command)")
    commands = root.add_subparsers(dest="command", required=True)
    for command in ("add", "list", "get", "update", "delete", "low-stock"):
        sub = commands.add_parser(command, allow_abbrev=False)
        if command in ("get", "update", "delete"):
            sub.add_argument("id", type=identifier)
        if command in ("add", "update"):
            for field, converter in (("name", name_value), ("price", price_value), ("quantity", natural)):
                sub.add_argument("--" + field, type=converter, required=command == "add")
        if command == "delete":
            sub.add_argument("--yes", action="store_true", required=True)
        if command == "low-stock":
            sub.add_argument("--threshold", type=natural, required=True)
    return root


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise StoreError("duplicate JSON key: " + key)
        result[key] = value
    return result


# CODING_AGENT_IDENTIFIED_FLAG: validate every record, even for read-only queries.
def validate(store):
    def require(condition):
        if not condition:
            raise StoreError("invalid inventory schema")
    require(type(store) is dict and set(store) == {"next_id", "products"})
    require(type(store["next_id"]) is int and store["next_id"] > 0)
    require(type(store["products"]) is list)
    seen = set()
    for product in store["products"]:
        require(type(product) is dict and set(product) == {"id", "name", "price", "quantity"})
        pid, name, price, qty = (product[k] for k in ("id", "name", "price", "quantity"))
        require(type(pid) is int and 0 < pid < store["next_id"] and pid not in seen)
        require(type(name) is str and bool(name) and name == name.strip())
        require(type(price) is str and re.fullmatch(r"(?:0|[1-9][0-9]*)\.[0-9]{2}", price) is not None)
        require(type(qty) is int and qty >= 0)
        seen.add(pid)


def read_store(path):
    try:
        with path.open(encoding="utf-8") as stream:
            store = json.load(stream, object_pairs_hook=unique_object)
    except FileNotFoundError:
        # A dangling symlink is an existing, unreadable store, not a new one.
        if path.is_symlink():
            raise StoreError("data path is a dangling symlink")
        return {"next_id": 1, "products": []}
    validate(store)
    return store


# CODING_AGENT_IDENTIFIED_FLAG: replace only after a complete successful write.
def save_store(path, store):
    content = json.dumps(store, ensure_ascii=True, indent=2) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".inventory-", suffix=".tmp", delete=False) as stream:
            temporary = stream.name
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)


def main(argv=None):
    root = parser()
    args = root.parse_args(argv)
    if args.command == "update" and all(getattr(args, key) is None for key in ("name", "price", "quantity")):
        root.error("update requires at least one of --name, --price, --quantity")
    try:
        path = Path(args.file)
        store = read_store(path)
        products = store["products"]
        if args.command in ("list", "low-stock"):
            result = sorted((p for p in products if args.command == "list" or p["quantity"] <= args.threshold),
                            key=lambda p: p["id"])
        elif args.command == "add":
            result = {"id": store["next_id"], "name": args.name, "price": args.price, "quantity": args.quantity}
            products.append(result)
            store["next_id"] += 1
        else:
            result = next((p for p in products if p["id"] == args.id), None)
            if result is None:
                raise StoreError(f"product ID {args.id} not found")
            if args.command == "update":
                for key in ("name", "price", "quantity"):
                    if getattr(args, key) is not None:
                        result[key] = getattr(args, key)
            elif args.command == "delete":
                products.remove(result)
                result = {"deleted_id": args.id}
        if args.command in ("add", "update", "delete"):
            save_store(path, store)
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except (StoreError, OSError, ValueError, UnicodeError, RecursionError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
