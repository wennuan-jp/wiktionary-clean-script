import argparse
import html
import os
import re
import xml.etree.ElementTree as ET


IGNORE_PREFIXES = (
    "wiktionary:",
    "template:",
    "category:",
    "module:",
    "user:",
    "talk:",
    "file:",
    "mediawiki:",
    "help:",
    "appendix:",
)

LANG_HEADER_RE = re.compile(r"^==\{\{L\|([a-z-]+)\}\}==\s*$")
GENERIC_H2_RE = re.compile(r"^==([^=]+)==\s*$")
TRANS_HEADER_RE = re.compile(r"^====\s*\{\{trans\}\}\s*====\s*$")
SECTION_HEADER_RE = re.compile(r"^(={2,4})[^=].*[^=]\1\s*$|^(={2,4})[^=]\2\s*$")
FILE_TAG_RE = re.compile(r"\[\[(?:File|Image):.+?\]\]", re.IGNORECASE | re.DOTALL)
INVALID_XML_CHAR_RE = re.compile(
    "[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]"
)
JAPANESE_TITLE_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


def local_name(tag):
    return tag.split("}")[-1]


def should_skip_title(title):
    title_lower = title.strip().lower()
    return (
        ":" in title_lower
        or any(title_lower.startswith(prefix) for prefix in IGNORE_PREFIXES)
        or not JAPANESE_TITLE_RE.search(title)
    )


def strip_non_japanese_language_blocks(text):
    if not text:
        return ""

    cleaned_lines = []
    skipping_language = False

    for line in text.splitlines():
        lang_match = LANG_HEADER_RE.match(line)
        if lang_match:
            skipping_language = lang_match.group(1) != "ja"
        elif GENERIC_H2_RE.match(line):
            skipping_language = False

        if not skipping_language:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def strip_translation_blocks(text):
    if not text:
        return ""

    cleaned_lines = []
    skipping_translation = False

    for line in text.splitlines():
        if TRANS_HEADER_RE.match(line):
            skipping_translation = True
            continue

        if skipping_translation and SECTION_HEADER_RE.match(line):
            skipping_translation = False

        if not skipping_translation:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def clean_page_text_completely(text):
    if not text:
        return ""

    text = strip_non_japanese_language_blocks(text)
    text = strip_translation_blocks(text)
    text = FILE_TAG_RE.sub("", text)
    text = INVALID_XML_CHAR_RE.sub("", text)
    return text.strip()


def extract_title_and_text(page_elem):
    title_text = ""
    text_content = ""

    for child in page_elem:
        child_tag = local_name(child.tag)
        if child_tag == "title" and child.text:
            title_text = child.text.strip()
        elif child_tag == "revision":
            for rev_child in child:
                if local_name(rev_child.tag) == "text" and rev_child.text:
                    text_content = clean_page_text_completely(rev_child.text)
                    break

    return title_text, text_content


def write_page(f, title_text, text_content, raw_text):
    f.write("  <page>\n")
    f.write(f"    <title>{html.escape(title_text, quote=False)}</title>\n")

    if raw_text:
        f.write(f'    <text xml:space="preserve">{text_content}</text>\n')
    else:
        f.write(
            f'    <text xml:space="preserve">{html.escape(text_content, quote=False)}</text>\n'
        )

    f.write("  </page>\n")


def purify_jawiktionary(input_file, output_file, raw_text=True, progress_every=50000):
    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

    page_count = 0
    saved_count = 0
    skipped_title_count = 0
    skipped_empty_count = 0

    with open(output_file, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write("<mediawiki>\n")

        context = ET.iterparse(input_file, events=("start", "end"))
        context = iter(context)
        _, root = next(context)

        for event, elem in context:
            if event != "end" or local_name(elem.tag) != "page":
                continue

            page_count += 1
            if progress_every and page_count % progress_every == 0:
                print(
                    f"scanned={page_count} saved={saved_count} "
                    f"skipped_title={skipped_title_count} skipped_empty={skipped_empty_count}"
                )

            title_text, text_content = extract_title_and_text(elem)

            if not title_text or should_skip_title(title_text):
                skipped_title_count += 1
            elif not text_content:
                skipped_empty_count += 1
            else:
                write_page(f, title_text, text_content, raw_text=raw_text)
                saved_count += 1

            elem.clear()
            root.clear()

        f.write("</mediawiki>\n")

    print("--- done ---")
    print(f"scanned pages: {page_count}")
    print(f"saved pages: {saved_count}")
    print(f"skipped by title: {skipped_title_count}")
    print(f"skipped empty text: {skipped_empty_count}")
    print(f"output: {output_file}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="One-pass jawiktionary purification pipeline."
    )
    parser.add_argument("input", nargs="?", default="jawiktionary0.xml")
    parser.add_argument("output", nargs="?", default="purified/jawikitionary.xml")
    parser.add_argument(
        "--escaped-text",
        action="store_true",
        help="Escape <, >, and & in text output so the result is strict XML.",
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
    purify_jawiktionary(
        args.input,
        args.output,
        raw_text=not args.escaped_text,
        progress_every=args.progress_every,
    )
