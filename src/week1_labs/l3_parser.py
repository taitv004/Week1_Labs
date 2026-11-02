import os
import json
import re
import logging
from pathlib import Path
from datetime import date, datetime
from pydantic import BaseModel, Field, ValidationError

# Cần cài các thư viện đọc file
from pypdf import PdfReader
from docx import Document
from bs4 import BeautifulSoup

# ==========================================
# CẤU HÌNH HỆ THỐNG LOGGING
# ==========================================
# Thiết lập định dạng log chuẩn mực: [Thời gian] [Cấp độ] [Vị trí] - Nội dung
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()  # In log ra màn hình console
    ]
)
logger = logging.getLogger("L3_Parser")


# ==========================================
# GIAI ĐOẠN 1: ĐỊNH NGHĨA DATA MODEL (PYDANTIC)
# ==========================================
class OrderMetadata(BaseModel):
    customer: str = Field(..., description="Tên khách hàng")
    po_number: str = Field(..., description="Mã số PO")
    order_date: date = Field(..., description="Ngày đặt hàng")

class ParsedPurchaseOrder(BaseModel):
    file_name: str
    metadata: OrderMetadata
    clean_text: str


# ==========================================
# GIAI ĐOẠN 2 & 3: PARSER & EXTRACTOR
# ==========================================
class DocumentParser:
    """Class chứa các hàm tĩnh để xử lý từng loại file và trích xuất dữ liệu"""

    @staticmethod
    def extract_metadata_from_text(file_name: str, text: str, ext: str) -> dict:
        """Dùng Regex SĂN LÙNG thông tin từ text thô (Clean Text) dựa theo định dạng file (ext)"""
        
        # 1. Tìm số PO
        po_match = re.search(r'(?:PO\s*(?:Number|#)?|Purchase\s*Order)[:\-]?\s*(ORD-\d{4}-\d{4})', text, re.IGNORECASE)
        if not po_match:
            po_match = re.search(r'(ORD-\d{4}-\d{4})', text)

        # 2. Tìm Ngày tháng
        date_match = re.search(r'(?:Order\s*)?Date[:\-]?\s*(\d{4}-\d{2}-\d{2})', text, re.IGNORECASE)
        if not date_match:
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)

        # 3. Tìm Khách hàng chia theo định dạng file (ext)
        customer_match = None
        
        if ext == ".docx":
            # DOCX: Tên nằm ngay sau chữ "Customer/Vendor:" trên cùng 1 dòng
            customer_match = re.search(r'(?i)Customer/Vendor[:\-]?\s*([^\n\r]+)', text)
            
        elif ext == ".pdf":
            # PDF: Tên nằm ở dòng ngay bên dưới nhãn "Vendor Details:"
            customer_match = re.search(r'(?i)Vendor Details[:\-]?\s*[\n\r]+([^\n\r]+)', text)
            
        elif ext == ".html":
            # HTML: Khi dùng BeautifulSoup get_text(), tên nằm ở dòng ngay bên dưới nhãn "Vendor Information"
            customer_match = re.search(r'(?i)Vendor Information[:\-]?\s*[\n\r]+([^\n\r]+)', text)
            
        else:
            # Fallback dự phòng cho các định dạng khác
            customer_match = re.search(r'(?i)(?:Customer|Vendor|Client|Buyer)(?:\s+Name)?[:\-]\s*([^\n\r]+)', text)

        extracted = {
            "customer": customer_match.group(1).strip() if customer_match else None,
            "po_number": po_match.group(1).strip() if po_match else None,
            "order_date": date_match.group(1).strip() if date_match else None
        }
        
        logger.debug(f"[{file_name}] Raw metadata trích xuất thô: {extracted}")
        return extracted
    
    @staticmethod
    def parse_pdf(file_path: Path) -> str:
        """Trích xuất Clean Text từ PDF"""
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()

    @staticmethod
    def parse_docx(file_path: Path) -> str:
        """Trích xuất Clean Text từ DOCX"""
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    text += f" {cell.text}"
        return text.strip()

    @staticmethod
    def parse_html(file_path: Path) -> str:
        """Trích xuất Clean Text từ HTML"""
        with open(file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
        return soup.get_text(separator='\n', strip=True)


# ==========================================
# GIAI ĐOẠN 4: MANAGER CHẠY LUỒNG CHÍNH
# ==========================================
def process_single_file(file_path: Path) -> dict:
    """Xử lý 1 file: Từ đọc file -> Trích xuất -> Trả về Pydantic Object hoặc Báo Lỗi"""
    file_name = file_path.name
    ext = file_path.suffix.lower()
    
    try:
        # 1. Gọi đúng hàm Parser dựa trên đuôi file
        if ext == ".pdf":
            clean_text = DocumentParser.parse_pdf(file_path)
        elif ext == ".docx":
            clean_text = DocumentParser.parse_docx(file_path)
        elif ext == ".html":
            clean_text = DocumentParser.parse_html(file_path)
        else:
            raise ValueError(f"Định dạng {ext} không được hỗ trợ.")

        # Kiểm tra nếu file rỗng / không lấy được text
        if not clean_text:
            raise ValueError("Không trích xuất được văn bản (File có thể bị hỏng).")

        # 2. Extract Metadata bằng Regex
        raw_metadata = DocumentParser.extract_metadata_from_text(file_name, clean_text, ext)
        
        # 3. Lắp vào Pydantic để ép kiểu và kiểm tra tính hợp lệ
        metadata_model = OrderMetadata(**raw_metadata)
        
        final_order = ParsedPurchaseOrder(
            file_name=file_name,
            metadata=metadata_model,
            clean_text=clean_text
        )
        
        logger.info(f" Thành công: {file_name} -> PO: {metadata_model.po_number}")
        return {"status": "success", "data": final_order.model_dump()}

    except ValidationError as ve:
        logger.warning(f" Lỗi cấu trúc/metadata ở file '{file_name}': Trường dữ liệu bị thiếu hoặc sai định dạng.")
        return {"status": "unsupported", "file": file_name, "error": f"Lỗi cấu trúc Metadata: Thiếu hoặc sai định dạng trường dữ liệu."}
    except Exception as e:
        logger.error(f" Lỗi vật lý/hỏng file ở '{file_name}': {str(e)}")
        return {"status": "broken", "file": file_name, "error": f"Lỗi xử lý file: {str(e)}"}


def main():
    # Xác định đường dẫn thư mục data tuyệt đối nằm ngoài src
    root = Path(__file__).resolve().parent.parent.parent
    input_folder = root / "data_lab3"
    
    if not input_folder.exists() or not input_folder.is_dir():
        logger.critical(f"Thư mục đầu vào không tồn tại hoặc không phải thư mục: {input_folder}")
        return

    output_file = "l3_parsed_results.json"
    
    results = {
        "successful_orders": [],
        "failed_orders": []
    }

    logger.info(f"Bắt đầu quét thư mục dữ liệu: {input_folder}")
    
    # Lặp qua tất cả các file trong thư mục
    for file_path in input_folder.glob("*.*"):
        logger.info(f"Đang xử lý: {file_path.name}...")
        result = process_single_file(file_path)
        
        if result["status"] == "success":
            results["successful_orders"].append(result["data"])
        else:
            results["failed_orders"].append({
                "file_name": result["file"],
                "reason": result["error"]
            })

    # Hàm chuyển đổi kiểu Date sang chuỗi JSON
    def date_encoder(obj):
        if isinstance(obj, (date, datetime)): 
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4, default=date_encoder)

    logger.info("=" * 50)
    logger.info(f"HOÀN THÀNH TOÀN BỘ PIPELINE:")
    logger.info(f"- Thành công: {len(results['successful_orders'])} file")
    logger.info(f"- Thất bại/Hỏng: {len(results['failed_orders'])} file")
    logger.info(f"- Kết quả đã xuất ra: {output_file}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()