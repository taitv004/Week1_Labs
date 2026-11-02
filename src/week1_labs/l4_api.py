import json
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

# Nhập khẩu trực tiếp "động cơ" và model từ Lab 3 của bạn
from week1_labs.l3_parser import DocumentParser, OrderMetadata, ParsedPurchaseOrder, logger

app = FastAPI(
    title="Purchase Order API (Lab 4)",
    description="API tự động hóa bóc tách và quản lý đơn hàng dựa trên Lab 3",
    version="1.0.0"
)

# Thư mục lưu file tạm thời khi người dùng upload
UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Bộ nhớ tạm (In-memory database) để lưu trữ các đơn hàng đã parse thành công trong phiên chạy
MEMORY_DB = []


# ==========================================
# GLOBAL ERROR HANDLER (Bộ xử lý lỗi toàn cục)
# ==========================================
@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Bắt lỗi cấu trúc/metadata khi dữ liệu thiếu hoặc sai kiểu dữ liệu"""
    logger.warning(f"Lỗi Pydantic Validation tại [{request.url.path}]: {exc.error_count()} lỗi được tìm thấy.")
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "error_type": "ValidationError",
            "message": "Dữ liệu không đáp ứng tiêu chuẩn cấu trúc Pydantic.",
            "details": exc.errors()
        }
    )


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Bắt các ngoại lệ HTTP chủ động (Ví dụ: 404 Not Found, 400 Bad Request)"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error_type": "HTTPException",
            "message": exc.detail
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Lưới lọc tổng cuối cùng: Bắt mọi lỗi hệ thống bất ngờ (500)"""
    logger.error(f"Lỗi hệ thống không xác định tại [{request.url.path}]: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_type": "InternalServerError",
            "message": "Đã xảy ra lỗi nội bộ phía máy chủ.",
            "detail": str(exc)
        }
    )


# ==========================================
# API ENDPOINTS
# ==========================================

@app.post("/purchase-orders", summary="Tải lên và phân tích tệp đơn hàng")
async def upload_and_parse_po(file: UploadFile = File(...)):
    """
    Endpoint nhận file upload (PDF, DOCX, HTML), chạy qua pipeline xử lý của Lab 3 
    và trả về dữ liệu cấu trúc đã được validate.
    """
    file_path = UPLOAD_DIR / file.filename
    ext = file_path.suffix.lower()

    # Kiểm tra nhanh định dạng được hỗ trợ
    if ext not in [".pdf", ".docx", ".html"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Định dạng tệp '{ext}' không được hỗ trợ. Chỉ chấp nhận .pdf, .docx, .html"
        )

    try:
        # 1. Lưu file tạm thời lên server
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. Gọi hàm Parser tương ứng từ Lab 3
        if ext == ".pdf":
            clean_text = DocumentParser.parse_pdf(file_path)
        elif ext == ".docx":
            clean_text = DocumentParser.parse_docx(file_path)
        elif ext == ".html":
            clean_text = DocumentParser.parse_html(file_path)

        if not clean_text:
            raise ValueError("Không thể trích xuất văn bản. Tệp có thể bị hỏng hoặc trống.")

        # 3. Trích xuất metadata thô bằng Regex theo định dạng ext
        raw_metadata = DocumentParser.extract_metadata_from_text(file.filename, clean_text, ext)

        # 4. Kiểm định dữ liệu qua Pydantic Model (Sẽ kích hoạt Global Error Handler nếu lỗi)
        metadata_model = OrderMetadata(**raw_metadata)

        final_order = ParsedPurchaseOrder(
            file_name=file.filename,
            metadata=metadata_model,
            clean_text=clean_text
        )

        order_dict = final_order.model_dump()

        # 5. Lưu vào bộ nhớ tạm (Memory DB) để phục vụ việc tra cứu qua GET
        # Kiểm tra xem PO này đã tồn tại trong DB chưa, nếu có rồi thì cập nhật, chưa thì thêm mới
        existing_index = next(
            (i for i, item in enumerate(MEMORY_DB) if item.get("metadata", {}).get("po_number") == metadata_model.po_number), 
            None
        )
        if existing_index is not None:
            MEMORY_DB[existing_index] = order_dict
        else:
            MEMORY_DB.append(order_dict)

        logger.info(f"API xử lý thành công tệp: {file.filename} -> PO: {metadata_model.po_number}")
        return {
            "status": "success",
            "message": "Phân tích đơn hàng thành công.",
            "data": order_dict
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    
    finally:
        # Luôn luôn dọn dẹp file tạm trên ổ đĩa tránh rác hệ thống
        if file_path.exists():
            file_path.unlink()


@app.get("/purchase-orders", summary="Lấy danh sách tất cả các đơn hàng đã parse")
async def get_all_purchase_orders():
    """Trả về toàn bộ danh sách đơn hàng đã được upload và xử lý thành công."""
    if not MEMORY_DB:
        raise HTTPException(
            status_code=404, 
            detail="Chưa có dữ liệu đơn hàng nào được tải lên trong phiên làm việc này."
        )
    return {
        "status": "success", 
        "count": len(MEMORY_DB), 
        "data": MEMORY_DB
    }


@app.get("/purchase-orders/{po_id}", summary="Tra cứu chi tiết đơn hàng theo mã PO")
async def get_purchase_order_by_id(po_id: str):
    """Tra cứu thông tin chi tiết của một đơn hàng cụ thể dựa vào mã số PO (Ví dụ: ORD-2026-0018)."""
    if not MEMORY_DB:
        raise HTTPException(status_code=404, detail="Kho dữ liệu đơn hàng chưa được khởi tạo.")

    # Tìm kiếm trong danh sách đơn hàng trong bộ nhớ
    for order in MEMORY_DB:
        if order.get("metadata", {}).get("po_number") == po_id:
            return {"status": "success", "data": order}

    # Nếu không tìm thấy mã PO tương ứng
    raise HTTPException(status_code=404, detail=f"Không tìm thấy đơn hàng nào với mã số PO: '{po_id}'")