from pathlib import Path
from fastapi.testclient import TestClient
from week1_labs.l4_api import app

# Khởi tạo client giả lập của FastAPI
client = TestClient(app)

# Xác định đường dẫn đến thư mục chứa file mẫu của Lab 3 (ví dụ: data_lab3)
SAMPLE_DATA_DIR = Path("../../data_lab3") 


def test_root_docs():
    """Kiểm tra xem trang tài liệu docs có mở được không"""
    response = client.get("/docs")
    assert response.status_code == 200


# def test_upload_valid_html_file():
#     """
#     Test 1: Upload một file HTML chuẩn có thật từ thư mục data_lab3
#     -> Kỳ vọng hệ thống parse thành công và trả về mã 200.
#     """
#     html_files = list(SAMPLE_DATA_DIR.glob("*.html"))
#     if not html_files:
#         assert True, "Bỏ qua test vì chưa có file html mẫu"
#         return
    
#     file_path = html_files[0]
    
#     with open(file_path, "rb") as f:
#         response = client.post(
#             "/purchase-orders",
#             files={"file": (file_path.name, f, "text/html")}
#         )
    
#     # In ra nội dung chi tiết nếu server trả về mã lỗi (để debug)
#     if response.status_code != 200:
#         print("\n[DEBUG] Server Error Response:", response.json())

#     assert response.status_code == 200
#     data = response.json()
#     assert data["status"] == "success"

def test_upload_corrupted_or_invalid_html_file():
    """
    Test trường hợp khách hàng upload một file HTML bị lỗi cấu trúc (ví dụ: PO_ORD-2026-0024.html)
    -> Kỳ vọng hệ thống phải từ chối, kích hoạt Global Error Handler và trả về mã 400.
    """
    # Chỉ định đích danh file bị lỗi cấu trúc từ thư mục mẫu
    file_path = SAMPLE_DATA_DIR / "PO_ORD-2026-0024.html"
    
    if not file_path.exists():
        assert True, "Bỏ qua test vì không tìm thấy file lỗi mẫu"
        return
    
    with open(file_path, "rb") as f:
        response = client.post(
            "/purchase-orders",
            files={"file": (file_path.name, f, "text/html")}
        )
    
    # Kỳ vọng hệ thống phải trả về mã lỗi 400 Bad Request
    assert response.status_code == 400
    
    # Kiểm tra xem cấu trúc JSON trả về có đúng chuẩn Global Error Handler không
    data = response.json()
    assert data["status"] == "error"
    assert "error_type" in data
    assert "message" in data

def test_upload_valid_pdf_file():
    """
    Test upload một file PDF chuẩn có thật từ thư mục data_lab3
    -> Kỳ vọng hệ thống parse thành công và trả về mã 200.
    """
    # Chỉ định đích danh một file PDF chuẩn đã được Lab 3 xử lý thành công

    pdf_files = list(SAMPLE_DATA_DIR.glob("*.pdf"))
    if not pdf_files:
        assert True, "Bỏ qua test vì chưa có file html mẫu"
        return
    file_path = pdf_files[0]
    
    if not file_path.exists():
        assert True, "Bỏ qua test vì không tìm thấy file PDF mẫu"
        return
    
    with open(file_path, "rb") as f:
        response = client.post(
            "/purchase-orders",
            files={"file": (file_path.name, f, "application/pdf")}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "metadata" in data["data"]

def test_upload_invalid_extension():
    """
    Test 2: Upload file sai định dạng (ví dụ file .txt)
    -> Kỳ vọng hệ thống từ chối và trả về mã lỗi 400.
    """
    files = {"file": ("malicious.txt", b"some random text data", "text/plain")}
    response = client.post("/purchase-orders", files=files)
    
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"


def test_get_all_purchase_orders():
    """
    Test 3: Gọi endpoint lấy danh sách toàn bộ đơn hàng (GET)
    -> Kỳ vọng nhận được mã 200 (nếu đã có file JSON kết quả) hoặc 404 (nếu chưa có).
    """
    response = client.get("/purchase-orders")
    assert response.status_code in [200, 404]


def test_get_po_by_id_success_or_not_found():
    """
    Test 4 & 5: Tra cứu đơn hàng theo mã PO cụ thể
    - Thử tìm một mã PO không có thật -> Kỳ vọng trả về 404 Not Found.
    """
    response = client.get("/purchase-orders/MA-PO-HOAN-TOAN-KHONG-TON-TAI-12345")
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"


def test_global_error_handler_triggered():
    """
    Test 6: Kiểm tra Global Error Handler phản hồi cấu trúc JSON chuẩn khi xảy ra lỗi
    """
    # Gửi request kỳ vọng gây lỗi 404 hoặc 400 để xem cấu trúc JSON trả về có đúng chuẩn không
    response = client.get("/purchase-orders/INVALID-ID-FOR-TEST")
    assert response.json()["status"] == "error"
    assert "error_type" in response.json()