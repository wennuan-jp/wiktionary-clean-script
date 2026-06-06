import argparse
import html
import os
import re
import sqlite3


PAGE_END = "</page>"
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.DOTALL)
TEXT_OPEN_RE = re.compile(r'<text\b[^>]*>', re.DOTALL)
TEXT_CLOSE = "</text>"
SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def iter_page_blocks(input_file):
    buffer = ""

    with open(input_file, "r", encoding="utf-8") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), ""):
            buffer += chunk

            while True:
                page_end = buffer.find(PAGE_END)
                if page_end == -1:
                    break

                page_block = buffer[: page_end + len(PAGE_END)]
                buffer = buffer[page_end + len(PAGE_END) :]

                if "<page>" in page_block:
                    yield page_block


def extract_page(page_block):
    title_match = TITLE_RE.search(page_block)
    if not title_match:
        return None, None

    text_open_match = TEXT_OPEN_RE.search(page_block, title_match.end())
    if not text_open_match:
        return None, None

    text_close = page_block.rfind(TEXT_CLOSE)
    if text_close == -1 or text_close < text_open_match.end():
        return None, None

    title = html.unescape(title_match.group(1)).strip()
    text = page_block[text_open_match.end() : text_close]
    return title, text


def connect_database(output_file):
    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    conn = sqlite3.connect(output_file)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def create_table(conn, table_name, replace_table):
    if not SQL_IDENTIFIER_RE.match(table_name):
        raise ValueError(
            "table name must start with a letter or underscore and contain only "
            "letters, numbers, and underscores"
        )

    if replace_table:
        conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')

    conn.execute(
        f'''
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            title TEXT PRIMARY KEY,
            text TEXT NOT NULL
        )
        '''
    )


def convert_purified_xml_to_sqlite(
    input_file,
    output_file,
    table_name="entries",
    replace_table=True,
    progress_every=50000,
):
    conn = connect_database(output_file)
    create_table(conn, table_name, replace_table)

    scanned_count = 0
    saved_count = 0
    skipped_count = 0

    try:
        with conn:
            for page_block in iter_page_blocks(input_file):
                scanned_count += 1
                title, text = extract_page(page_block)

                if not title or text is None:
                    skipped_count += 1
                    continue

                conn.execute(
                    f'INSERT OR REPLACE INTO "{table_name}" (title, text) VALUES (?, ?)',
                    (title, text),
                )
                saved_count += 1

                if progress_every and scanned_count % progress_every == 0:
                    print(
                        f"scanned={scanned_count} saved={saved_count} "
                        f"skipped={skipped_count}"
                    )
    finally:
        conn.close()

    print("--- done ---")
    print(f"scanned pages: {scanned_count}")
    print(f"saved rows: {saved_count}")
    print(f"skipped malformed pages: {skipped_count}")
    print(f"output: {output_file}")
    print(f"table: {table_name}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert purified jawiktionary XML output into a SQLite table."
    )
    parser.add_argument("input", nargs="?", default="purified/jawikitionary.xml")
    parser.add_argument("output", nargs="?", default="purified/jawikitionary.sqlite")
    parser.add_argument(
        "--table",
        default="entries",
        help="SQLite table name to create or replace.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append/replace rows in the existing table instead of dropping it first.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=50000,
        help="Print progress every N pages. Use 0 to disable.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    convert_purified_xml_to_sqlite(
        args.input,
        args.output,
        table_name=args.table,
        replace_table=not args.append,
        progress_every=args.progress_every,
    )
