import os
import re
import sys
import json
import time
import shutil

# Cấu hình UTF-8 cho Windows Terminal
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# ==============================================================================
# ⚙️ CẤU HÌNH CÔNG TẮC BẬT/TẮT MÀN HÌNH TRÌNH DUYỆT (PLAYWRIGHT)
# - Đặt SHOW_BROWSER_UI = True  -> Mở cửa sổ trình duyệt trên màn hình (để tự bấm tick Captcha nếu có)
# - Đặt SHOW_BROWSER_UI = False -> Ẩn trình duyệt chạy trong nền
# ==============================================================================
SHOW_BROWSER_UI = True


def extract_so_hieu(text: str, source_path: str = "") -> str:
    """
    Trích xuất số hiệu văn bản pháp luật chuẩn xác từ:
    1. 35 dòng đầu tiên của văn bản (Header Section)
    2. Tên file hoặc đường link URL (Fallback)
    """
    if text:
        header_lines = "\n".join([line.strip() for line in text.split("\n")[:40] if line.strip()])
        
        so_match = re.search(r'Số\s*[\:\s]\s*([\d\/\w\-\.\_]+)', header_lines, re.IGNORECASE)
        if so_match and ('/' in so_match.group(1) or '-' in so_match.group(1)):
            return so_match.group(1).strip()
            
        luat_so_match = re.search(r'(?:Luật|Nghị định|Quyết định|Thông tư)\s+số\s*[\:\s]\s*([\d\/\w\-\.\_]+)', header_lines, re.IGNORECASE)
        if luat_so_match:
            return luat_so_match.group(1).strip()

        gen_match = re.search(r'\b(\d+\/\d+\/(?:NĐ\-CP|QH\d+|TT|QĐ|NĐ))\b', header_lines, re.IGNORECASE)
        if gen_match:
            return gen_match.group(1).strip()

    if source_path:
        fname_match = re.search(r'(\d+)[\-_](\d{4})[\-_](qh\d+|nd\-cp|tt|qd)', source_path, re.IGNORECASE)
        if fname_match:
            num, year, type_str = fname_match.group(1), fname_match.group(2), fname_match.group(3).upper()
            if type_str == "ND-CP":
                type_str = "NĐ-CP"
            return f"{num}/{year}/{type_str}"

    return "N/A"


def convert_table_matrix_to_narrative(matrix: list) -> str:
    """
    Hàm chuyển đổi ma trận bảng 2D thành các câu văn ngữ cảnh (Row-by-Row Narrative).
    Đảm bảo 100% dữ liệu từng ô được gắn đúng với Tên Cột tương ứng.
    """
    if not matrix or len(matrix) < 2:
        return ""

    cleaned_matrix = []
    for row in matrix:
        if not row:
            continue
        cleaned_matrix.append([re.sub(r'\s+', ' ', str(cell or '')).strip() for cell in row])

    headers = cleaned_matrix[0]
    headers = [h if h else f"Cột {i+1}" for i, h in enumerate(headers)]

    narrative_lines = ["[BẢNG THÔNG TIN:]"]
    for r_idx, row in enumerate(cleaned_matrix[1:]):
        row_parts = []
        for c_idx, val in enumerate(row):
            if c_idx < len(headers) and val:
                col_name = headers[c_idx]
                row_parts.append(f"{col_name}: {val}")
        if row_parts:
            row_title = row[1] if len(row) > 1 and row[1] else f"Mục {r_idx+1}"
            narrative_lines.append(f"• {row_title}: " + " | ".join(row_parts))

    return "\n".join(narrative_lines)


class DocumentLoader:
    """
    Nạp các tệp văn bản luật thô từ thư mục data/raw/
    Hỗ trợ nạp file địa phương (.pdf, .txt, .html) và cào trực tiếp từ đường dẫn URL trong urls.json.
    Tích hợp Khoanh Vùng Nội Dung Chuẩn Xác trước khi bóc tách Bảng.
    """
    def __init__(self, raw_dir: str):
        self.raw_dir = raw_dir

    def load_documents(self):
        docs = []
        if not os.path.exists(self.raw_dir):
            print(f"[!] Thư mục '{self.raw_dir}' không tồn tại.")
            return docs

        # 1. Nạp từ các file địa phương (.txt, .html, .pdf)
        for fname in os.listdir(self.raw_dir):
            fpath = os.path.join(self.raw_dir, fname)
            content = ""

            if fname.endswith(".txt"):
                with open(fpath, "r", encoding="utf-8") as f:
                    raw_txt = f.read()
                    content = self._parse_txt_tables(raw_txt)

            elif fname.endswith(".html"):
                with open(fpath, "r", encoding="utf-8") as f:
                    raw_html = f.read()
                    content = self._clean_and_extract_main_content(raw_html)

            elif fname.endswith(".pdf"):
                content = self._read_pdf_file(fpath)

            if content:
                raw_blocks = content.split("---")
                for block in raw_blocks:
                    block = block.strip()
                    if not block:
                        continue

                    so_hieu = extract_so_hieu(block, fname)
                    ten_vb_match = re.search(r'TÊN VĂN BẢN:\s*(.+)', block, re.IGNORECASE)
                    ngay_bh_match = re.search(r'NGÀY BAN HÀNH:\s*(.+)', block, re.IGNORECASE)

                    ten_van_ban = ten_vb_match.group(1).strip() if ten_vb_match else fname
                    ngay_ban_hanh = ngay_bh_match.group(1).strip() if ngay_bh_match else "N/A"

                    docs.append({
                        "source_type": "file",
                        "source": f"file://data/raw/{fname}",
                        "filename": fname,
                        "so_hieu": so_hieu,
                        "ten_van_ban": ten_van_ban,
                        "ngay_ban_hanh": ngay_ban_hanh,
                        "raw_content": block
                    })

        # 2. Cào từ danh sách URL (nếu có file data/raw/urls.json)
        urls_file = os.path.join(self.raw_dir, "urls.json")
        if os.path.exists(urls_file):
            try:
                with open(urls_file, "r", encoding="utf-8") as f:
                    url_items = json.load(f)
                for item in url_items:
                    url = item.get("url")
                    if url and url.startswith("http"):
                        crawled_doc = self.crawl_url(url, title=item.get("title", ""))
                        if crawled_doc:
                            docs.append(crawled_doc)
            except Exception as e:
                print(f"[!] Lỗi khi nạp urls.json: {e}")

        return docs

    def _read_pdf_file(self, fpath: str) -> str:
        """Đọc văn bản & bóc tách Bảng từ file PDF bằng pdfplumber."""
        try:
            import pdfplumber
            print(f"[+] Đang đọc & bóc tách Bảng từ file PDF bằng pdfplumber: '{os.path.basename(fpath)}'...")
            
            extracted_pages = []
            with pdfplumber.open(fpath) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    
                    tables = page.extract_tables()
                    if tables:
                        for tbl in tables:
                            table_narrative = convert_table_matrix_to_narrative(tbl)
                            if table_narrative:
                                page_text += "\n" + table_narrative

                    if page_text:
                        extracted_pages.append(page_text)

            full_pdf_text = "\n".join(extracted_pages)
            print(f"[🎉] Đã trích xuất thành công {len(extracted_pages)} trang từ PDF.")
            return full_pdf_text

        except ImportError:
            try:
                from pypdf import PdfReader
                print(f"[+] Đọc PDF bằng pypdf: '{os.path.basename(fpath)}'...")
                reader = PdfReader(fpath)
                extracted_pages = [p.extract_text() for p in reader.pages if p.extract_text()]
                return "\n".join(extracted_pages)
            except Exception as e:
                print(f"[!] Lỗi khi đọc file PDF '{fpath}': {e}")
        except Exception as e:
            print(f"[!] Lỗi khi bóc tách PDF bằng pdfplumber '{fpath}': {e}")
        return ""

    def _parse_txt_tables(self, raw_txt: str) -> str:
        lines = raw_txt.split("\n")
        parsed_lines = []
        table_buffer = []

        for line in lines:
            if "|" in line:
                cells = [c.strip() for c in line.split("|") if c.strip()]
                if len(cells) >= 2:
                    table_buffer.append(cells)
                    continue

            if table_buffer:
                parsed_lines.append(convert_table_matrix_to_narrative(table_buffer))
                table_buffer = []

            parsed_lines.append(line)

        if table_buffer:
            parsed_lines.append(convert_table_matrix_to_narrative(table_buffer))

        return "\n".join(parsed_lines)

    def crawl_url(self, url: str, title: str = "") -> dict:
        print(f"[+] Đang cào dữ liệu từ URL: {url}")
        text_content = self._crawl_with_requests(url)
        
        if not text_content:
            mode_str = "MỞ CỬA SỔ TRÌNH DUYỆT" if SHOW_BROWSER_UI else "ẨN TRÌNH DUYỆT BÊN DƯỚI"
            print(f"[🚀] Phát hiện tường lửa Cloudflare -> Đang khởi chạy Playwright ({mode_str})...")
            text_content = self._crawl_with_playwright_stealth(url)

        if not text_content:
            print(f"[!] Không thể cào được nội dung từ URL: {url}")
            return None

        so_hieu = extract_so_hieu(text_content, url)

        return {
            "source_type": "url",
            "source": url,
            "filename": url,
            "so_hieu": so_hieu,
            "ten_van_ban": title or "Văn bản Luật cào từ URL",
            "ngay_ban_hanh": "N/A",
            "raw_content": text_content
        }

    def _clean_and_extract_main_content(self, html_content: str) -> str:
        """
        Hàm bóc tách chuẩn xác khung chứa toàn văn bài luật #divContent.
        Ưu tiên cô lập đúng Khung bài luật #divContent TRƯỚC, rồi mới bóc tách Bảng bên trong.
        Cực kỳ an toàn, không bị phá vỡ cấu trúc DOM trang web.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")
        
        # 1. Xóa các thẻ rác không thuộc bài luật
        for s in soup(["script", "style", "header", "footer", "nav", "iframe", "aside"]):
            s.decompose()

        # 2. Ưu tiên khoanh vùng duy nhất Khung bài luật chính #divContent trước
        target_container = (
            soup.find(id="divContent") or 
            soup.find(id="divContentText") or
            soup.find("div", class_="content1") or
            soup.find("div", id="content1") or
            soup.find(class_=re.compile(r'content\-law|doc_content|fulltext', re.I))
        )

        if not target_container:
            divs = soup.find_all("div")
            if divs:
                target_container = max(divs, key=lambda d: len(d.get_text()))
            else:
                target_container = soup

        # 3. CHỈ bóc tách các thẻ <table> NẰM BÊN TRONG khung bài luật target_container
        for table_tag in target_container.find_all("table"):
            rows = table_tag.find_all("tr")
            matrix = []
            for r in rows:
                row_cells = [td.get_text() for td in r.find_all(["th", "td"])]
                if row_cells:
                    matrix.append(row_cells)
            
            table_narrative = convert_table_matrix_to_narrative(matrix)
            if table_narrative:
                narrative_p = soup.new_tag("p")
                narrative_p.string = "\n" + table_narrative + "\n"
                table_tag.replace_with(narrative_p)

        return target_container.get_text(separator="\n")

    def _crawl_with_requests(self, url: str) -> str:
        try:
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200 and "Just a moment..." not in resp.text:
                return self._clean_and_extract_main_content(resp.text)
        except Exception:
            pass
        return None

    def _crawl_with_playwright_stealth(self, url: str) -> str:
        user_dir = os.path.abspath(os.path.join(self.raw_dir, "..", "browser_user_data"))
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                launch_args = ['--disable-blink-features=AutomationControlled', '--no-sandbox']
                if not SHOW_BROWSER_UI:
                    launch_args.append('--headless=new')

                context = p.chromium.launch_persistent_context(
                    user_data_dir=user_dir,
                    headless=not SHOW_BROWSER_UI,
                    args=launch_args,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    locale="vi-VN"
                )
                
                page = context.pages[0] if context.pages else context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                print("[+] Đang nạp trang web. Nếu có Captcha, hãy bấm tick vào ô xác minh trên màn hình...")
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                except Exception as e:
                    print(f"[!] Chờ nạp trang: {e}")
                
                # Chờ người dùng bấm Captcha và trang web chuyển hướng nạp toàn văn bài luật (tối đa 90s)
                start_time = time.time()
                content_found = False

                while time.time() - start_time < 90:
                    try:
                        title = page.title()
                        if "Just a moment" not in title and "Chờ một chút" not in title:
                            elem = page.query_selector("#divContent, .content1, #divContentText, main, body")
                            if elem:
                                time.sleep(3)  # Chờ 3s cho DOM render 100% toàn văn
                                content_found = True
                                print("[🎉] Đã nạp thành công trang bài luật toàn văn!")
                                break
                    except Exception:
                        pass
                    time.sleep(1)

                try:
                    html_content = page.content()
                except Exception:
                    time.sleep(2)
                    html_content = page.content()

                context.close()

                text = self._clean_and_extract_main_content(html_content)
                if len(text) < 1500:
                    print(f"[!] Nội dung cào ra quá ngắn ({len(text)} ký tự, có thể chưa qua Captcha). Bỏ qua URL này.")
                    return None

                print(f"[🎉] Vượt bot thành công! Đã trích xuất {len(text)} ký tự bài luật toàn văn.")
                return text
        except Exception as e:
            print(f"[!] Playwright cào thất bại: {e}")
            return None
        finally:
            if os.path.exists(user_dir):
                shutil.rmtree(user_dir, ignore_errors=True)


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_dir = os.path.abspath(os.path.join(script_dir, "..", "data", "raw"))
    loader = DocumentLoader(raw_dir)
    documents = loader.load_documents()
    print(f"[+] Đã nạp thành công {len(documents)} văn bản luật thô.")
