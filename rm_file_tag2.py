import re
import xml.etree.ElementTree as ET


def clean_page_text_completely(text):
    if not text:
        return ""

    # 1. Remove [[File:...]] and [[Image:...]] tags
    file_tag_regex = re.compile(
        r"\[\[(?:File|Image):.+?\]\]", re.IGNORECASE | re.DOTALL
    )
    text = file_tag_regex.sub("", text)

    # 2. (Optional) Put your language filtering or other text processing logic here

    return text.strip()


def strip_files_from_xml(input_file, output_file):
    print("正在從 XML 中移除所有圖片與檔案標籤...")

    ns_regex = re.compile(r"ns\d+:")
    xmlns_regex = re.compile(r'\s?xmlns:ns\d+="[^"]+"')

    with open(output_file, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write("<mediawiki>\n")

        context = ET.iterparse(input_file, events=("start", "end"))
        context = iter(context)
        event, root = next(context)

        for event, elem in context:
            local_tag = elem.tag.split("}")[-1]

            if event == "end" and local_tag == "page":
                # Deep-dive to find the <text> tag
                for child in elem:
                    if child.tag.split("}")[-1] == "revision":
                        for rev_child in child:
                            if rev_child.tag.split("}")[-1] == "text":
                                if rev_child.text:
                                    # Execute the stripping
                                    rev_child.text = clean_page_text_completely(
                                        rev_child.text
                                    )

                                    # Recalculate bytes for database accuracy
                                    if "bytes" in rev_child.attrib:
                                        rev_child.attrib["bytes"] = str(
                                            len(rev_child.text.encode("utf-8"))
                                        )
                                break
                        break

                # Write out cleaned page string
                page_xml = ET.tostring(elem, encoding="utf-8").decode("utf-8")
                page_xml = ns_regex.sub("", page_xml)
                page_xml = xmlns_regex.sub("", page_xml)
                f.write("  " + page_xml + "\n")

                elem.clear()
                root.clear()

        f.write("</mediawiki>\n")
    print("--- 檔案標籤移除完成！ ---")


if __name__ == "__main__":
    strip_files_from_xml("pure_ja_wiktionary2.xml", "no_files_wiktionary3.xml")
