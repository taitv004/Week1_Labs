import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Biểu thức chính quy (Regex) tìm mã định dạng ORD-YYYY-NNNN
ORDER_CODE_PATTERN = re.compile(r"ORD-\d{4}-\d{4}")


@dataclass
class CustomerInfo:
    """Dataclass chứa thông tin khách hàng được map từ mảng 'customers'."""
    id: int
    code: str
    name: str
    tier: str
    city: str
    contactEmail: str
    contactPhone: str


@dataclass
class MatchedOrder:
    """Dataclass chứa thông tin đơn hàng và thông tin khách hàng đi kèm."""
    order_code: str
    status: str
    total: int
    currency: str
    customer: CustomerInfo | None


@dataclass
class DocumentMatch:
    """Dataclass đại diện cho 1 file văn bản và danh sách các đơn hàng tìm được bên trong."""
    document: str
    mentioned_orders: list[MatchedOrder]


def load_database(db_path: Path) -> tuple[dict[str, Any], dict[int, CustomerInfo]]:
    """
    Đọc file db.json và tạo ra 2 từ điển (dictionaries) để tra cứu nhanh (O(1)):
    - orders_db: key là mã đơn hàng (ví dụ: 'ORD-2026-0001'), value là dữ liệu order.
    - customers_db: key là ID khách hàng, value là object CustomerInfo.
    """
    with open(db_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Build bảng tra cứu Khách hàng
    customers_db: dict[int, CustomerInfo] = {}
    for c in data.get("customers", []):
        customers_db[c["id"]] = CustomerInfo(
            id=c.get("id", 0),
            code=c.get("code", ""),
            name=c.get("name", ""),
            tier=c.get("tier", ""),
            city=c.get("city", ""),
            contactEmail=c.get("contactEmail", ""),
            contactPhone=c.get("contactPhone", "")
        )

    # 2. Build bảng tra cứu Đơn hàng
    orders_db: dict[str, Any] = {}
    for o in data.get("orders", []):
        # print(o["code"])
        orders_db[o["code"]] = o

    return orders_db, customers_db


def process_text(text: str, doc_name: str, orders_db: dict[str, Any], customers_db: dict[int, CustomerInfo]) -> DocumentMatch | None:
    """
    Chuẩn hóa văn bản, quét Regex, map với DB và trả về đối tượng DocumentMatch.
    """
    normalized_text = " ".join(text.split())
    
    # ---------------------------------------------------------
    # DEBUGGER BREAKPOINT (Yêu cầu của mentor)
    # ---------------------------------------------------------
    # breakpoint()

    extracted_codes = sorted(set(ORDER_CODE_PATTERN.findall(normalized_text)))
    if not extracted_codes:
        return None

    matched_orders: list[MatchedOrder] = []
    
    for code in extracted_codes:
        order_data = orders_db.get(code)

        # print(order_data)  # In ra dữ liệu đơn hàng tìm được từ DB (nếu có)
        
        if order_data:
            # Nếu tìm thấy đơn hàng trong DB, lấy tiếp customerId để tìm khách hàng
            cust_id = order_data.get("customerId")
            customer_info = customers_db.get(cust_id) if cust_id else None
            
            matched_orders.append(MatchedOrder(
                order_code=code,
                status=order_data.get("status", "UNKNOWN"),
                total=order_data.get("total", 0),
                currency=order_data.get("currency", "VND"),
                customer=customer_info
            ))
        else:
            # Nếu mã nằm trong text nhưng không có trong DB
            matched_orders.append(MatchedOrder(
                order_code=code,
                status="NOT_FOUND_IN_DB",
                total=0,
                currency="",
                customer=None
            ))

    return DocumentMatch(document=doc_name, mentioned_orders=matched_orders)


def main() -> None:
    parser = argparse.ArgumentParser(description="L1 Order Document Toolkit (with Relational DB lookup)")
    # parser.add_argument("--docs", type=str, required=True, help="Thư mục (hoặc file) chứa email/ghi chú cần quét")
    parser.add_argument("--db", type=str, required=True, help="Đường dẫn đến file db.json để tra cứu và quét")
    parser.add_argument("--out", type=str, default="report.json", help="File JSON đầu ra")
    args = parser.parse_args()

    results: list[DocumentMatch] = []

    db_path = Path(args.db)
    # docs_path = Path(args.docs)

    if not db_path.exists() or not db_path.is_file():
        print(f"Lỗi: Không tìm thấy file cơ sở dữ liệu '{db_path}'.")
        return
    # if not docs_path.exists():
    #     print(f"Lỗi: Không tìm thấy thư mục/file tài liệu '{docs_path}'.")
    #     return

    # Tao du lieu de lay OrderID
    with open(db_path, "r", encoding="utf-8") as f:
                    content = f.read()

    # Tao Co so du lieu cho Order va Customer
    print("Đang nạp cơ sở dữ liệu vào bộ nhớ...")
    orders_db, customers_db = load_database(db_path)

    match = process_text(content, db_path.name, orders_db, customers_db)
    try: 
        if match:
            results.append(match)
    except OSError as e:
                print(f"Lỗi truy cập file {db_path.name}: {e}")

    

    # if docs_path.is_file():
    #     print(f"Đang quét file: {docs_path.name}...")
    #     try:
    #         with open(docs_path, "r", encoding="utf-8") as f:
    #             content = f.read()
    #         match = process_text(content, docs_path.name, orders_db, customers_db)
    #         if match:
    #             results.append(match)
    #     except OSError as e:
    #         print(f"Lỗi truy cập file {docs_path.name}: {e}")

    # elif docs_path.is_dir():
    #     print(f"Đang quét thư mục: {docs_path}...")
    #     for filepath in docs_path.rglob("*"):
    #         if filepath.is_file():
    #             try:
    #                 with open(filepath, "r", encoding="utf-8") as f:
    #                     content = f.read()
                    
    #                 doc_name = str(filepath.relative_to(docs_path))
    #                 match = process_text(content, doc_name, orders_db, customers_db)
                    
    #                 if match:
    #                     results.append(match)
    #             except UnicodeDecodeError:
    #                 continue
    #             except OSError as e:
    #                 print(f"Lỗi truy cập file {filepath.name}: {e}")

    out_path = Path(args.out)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, indent=4, ensure_ascii=False)

    print(f"Hoàn tất! Tìm thấy {len(results)} tài liệu chứa mã đơn hàng hợp lệ.")
    print(f"Báo cáo chi tiết đã lưu tại: {out_path.absolute()}")


if __name__ == "__main__":
    main()