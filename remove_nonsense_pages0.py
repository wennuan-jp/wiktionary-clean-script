import re
import xml.etree.ElementTree as ET

# 擴充過濾清單，加入 mediawiki、特別注意大小寫與帶冒號的形式
IGNORE_PREFIXES = (
    "wiktionary:",
    "template:",
    "category:",
    "module:",
    "user:",
    "talk:",
    "file:",
    "mediawiki:",  # 修正你範例中漏掉的 MediaWiki 系統提示
    "help:",
    "appendix:",
)


def filter_wiktionary_xml_v2(input_file, output_file):
    print("開始處理 XML 檔案 (v2 升級版)...")

    # 用來強力拔除 XML 輸出時自動帶上的 ns0: 這種髒前綴
    # 這樣輸出的 XML 就會保持非常乾淨的 <page><title> 格式
    ns_regex = re.compile(r"ns\d+:")
    xmlns_regex = re.compile(r'\s?xmlns:ns\d+="[^"]+"')

    with open(output_file, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write("<mediawiki>\n")

        # 使用 iterparse 串流讀取
        context = ET.iterparse(input_file, events=("start", "end"))
        context = iter(context)
        event, root = next(context)

        page_count = 0
        saved_count = 0

        for event, elem in context:
            # 使用 localname 匹配，不管有沒有 ns0: 只要結尾是 page 就處理
            local_tag = elem.tag.split("}")[-1]

            if event == "end" and local_tag == "page":
                page_count += 1
                if page_count % 50000 == 0:
                    print(f"已掃描 {page_count} 個頁面...")

                # 萬用匹配：尋找不論帶有何種命名空間的 title
                title_elem = None
                for child in elem:
                    if child.tag.split("}")[-1] == "title":
                        title_elem = child
                        break

                if title_elem is not None and title_elem.text:
                    title_text_lower = title_elem.text.strip().lower()

                    # 【核心修改】只要標題裡面含有冒號 ":"，直接丟棄！
                    if ":" in title_text_lower:
                        elem.clear()
                        root.clear()
                        continue

                    # 檢查是否命中過濾前綴
                    if any(
                        title_text_lower.startswith(prefix)
                        for prefix in IGNORE_PREFIXES
                    ):
                        elem.clear()
                        root.clear()
                        continue

                # 通過篩選，轉成字串
                page_xml = ET.tostring(elem, encoding="utf-8").decode("utf-8")

                # 【核心修正】強力清洗：把 xml 裡面自帶的 ns0: 和 xmlns:ns0 全都擦掉
                page_xml = ns_regex.sub("", page_xml)
                page_xml = xmlns_regex.sub("", page_xml)

                f.write("  " + page_xml + "\n")
                saved_count += 1

                elem.clear()
                root.clear()

        f.write("</mediawiki>\n")

    print("--- 處理完成 ---")
    print(f"總共掃描頁面: {page_count}")
    print(f"保留有效頁面: {saved_count}")


if __name__ == "__main__":
    # 填入你的檔案名稱
    input_xml = "jawiktionary.xml"
    output_xml = "clean_jawiktionary.xml"

    filter_wiktionary_xml_v2(input_xml, output_xml)
