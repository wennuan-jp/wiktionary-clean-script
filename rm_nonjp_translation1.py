import re
import xml.etree.ElementTree as ET


def process_wikitext_strip_languages(text):
    if not text:
        return ""

    lines = text.splitlines()
    cleaned_lines = []

    # State tracking: Are we currently inside a skipped language block?
    skipping_language = False

    # Regex to detect a Level 2 language heading: =={{L|code}}==
    # Captures the language code to see if it's 'ja' or something else
    lang_header_regex = re.compile(r"^==\{\{L\|([a-z-]+)\}\}==\s*$")

    # Regex to detect ANY other Level 2 heading: ==Heading==
    generic_h2_regex = re.compile(r"^==([^=]+)==\s*$")

    for line in lines:
        # 1. Check if the line is a Language H2 block
        lang_match = lang_header_regex.match(line)
        if lang_match:
            lang_code = lang_match.group(1)
            if lang_code == "ja":
                skipping_language = False  # Keep Japanese
            else:
                skipping_language = True  # Skip any other language (zh, ko, vi, etc.)

        # 2. Check if the line is a non-language H2 block (e.g., ==漢字==)
        elif generic_h2_regex.match(line):
            skipping_language = False  # Never skip native generic blocks

        # 3. If we are not in a skip-state, preserve the line
        if not skipping_language:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def clean_internal_languages(input_file, output_file):
    print("開始深層清洗：正在移除日文以外的語言區塊...")

    ns_regex = re.compile(r"ns\d+:")
    xmlns_regex = re.compile(r'\s?xmlns:ns\d+="[^"]+"')

    with open(output_file, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write("<mediawiki>\n")

        context = ET.iterparse(input_file, events=("start", "end"))
        context = iter(context)
        event, root = next(context)

        processed_count = 0

        for event, elem in context:
            local_tag = elem.tag.split("}")[-1]

            if event == "end" and local_tag == "page":
                processed_count += 1
                if processed_count % 20000 == 0:
                    print(f"已處理 {processed_count} 個詞條內文...")

                # 尋找 <text> 標籤
                text_elem = None
                for child in elem:
                    if child.tag.split("}")[-1] == "revision":
                        for rev_child in child:
                            if rev_child.tag.split("}")[-1] == "text":
                                text_elem = rev_child
                                break
                        break

                # 如果有找到內文，進行加工
                if text_elem is not None and text_elem.text:
                    # 執行核心過濾演算法
                    cleaned_text = process_wikitext_strip_languages(text_elem.text)
                    text_elem.text = cleaned_text

                    # 更新 bytes 屬性以確保 XML 的準確性 (選做，但對某些解析器安全)
                    if "bytes" in text_elem.attrib:
                        text_elem.attrib["bytes"] = str(
                            len(cleaned_text.encode("utf-8"))
                        )

                # 轉回字串並寫入
                page_xml = ET.tostring(elem, encoding="utf-8").decode("utf-8")
                page_xml = ns_regex.sub("", page_xml)
                page_xml = xmlns_regex.sub("", page_xml)

                f.write("  " + page_xml + "\n")

                elem.clear()
                root.clear()

        f.write("</mediawiki>\n")
    print(f"--- 清洗完成！共優化了 {processed_count} 個頁面的內部結構 ---")


if __name__ == "__main__":
    # 使用你剛才切好的檔案作為輸入
    input_xml = "clean_jawiktionary.xml"
    output_xml = "pure_ja_wiktionary.xml"

    clean_internal_languages(input_xml, output_xml)
