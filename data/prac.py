# from pydantic import BaseModel, Field, ValidationError
import asyncio

# # 1. Định nghĩa khuôn mẫu (Model)
# class UserProfile(BaseModel):
#     name: str
#     age: int = Field(ge=18)  # ge=18 nghĩa là Greater than or Equal to 18 (>= 18)
#     email: str = "chưa có"

# # --- TRƯỜNG HỢP 1: Dữ liệu chuẩn chỉnh ---
# print("--- TRƯỜNG HỢP 1: Dữ liệu hợp lệ ---")
# try:
#     # Dữ liệu đầu vào giả lập
#     raw_data = {"name": "Nguyễn Văn A", "age": 25, "email": "a@gmail.com"}
    
#     # Đưa qua Pydantic kiểm duyệt
#     user = UserProfile.model_validate(raw_data)
    
#     print(f"Thành công! Tên: {user.name}, Tuổi: {user.age}")
# except ValidationError as e:
#     print(e)


# # --- TRƯỜNG HỢP 2: Dữ liệu vi phạm quy tắc (Dưới 18 tuổi) ---
# print("\n--- TRƯỜNG HỢP 2: Dữ liệu vi phạm (Dưới 18 tuổi) ---")
# try:
#     bad_data = {"name": "Bé B", "age": 15}  # Vi phạm điều kiện age >= 18
    
#     user = UserProfile.model_validate(bad_data)
#     print("Thành công!")
# except ValidationError as e:
#     print("Pydantic đã chặn lại thành công với lỗi:")
#     print(e)

# from pydantic import BaseModel

# # 1. Định nghĩa một Model đơn giản cho Sản phẩm
# class Product(BaseModel):
#     name: str
#     price: float
#     in_stock: bool = True  # Giá trị mặc định nếu không truyền vào

# # --- 1. Tạo đối tượng trực tiếp (Không cần try...except vì dữ liệu nội bộ) ---
# item1 = Product(name="Bàn phím cơ", price=1500000)
# print("--- Ví dụ 1: Khởi tạo trực tiếp ---")
# print(item1)  # In ra dạng đối tượng Pydantic đẹp mắt
# print(f"Tên sản phẩm: {item1.name}, Giá: {item1.price}\n")


# # --- 2. Dùng model_validate() với dữ liệu thô (Dictionary từ API hoặc JSON) ---
# raw_data = {"name": "Chuột không dây", "price": 450000, "in_stock": False}

# item2 = Product.model_validate(raw_data)
# print("--- Ví dụ 2: Dùng model_validate() ---")
# print(type(item2))  # Kiểu dữ liệu trả về là Product
# print(f"Đã kiểm duyệt thành công sản phẩm: {item2.name} (Còn hàng: {item2.in_stock})\n")


# # --- 3. Dùng model_dump() để đổi ngược lại thành từ điển Python (dict) ---
# python_dict = item2.model_dump()
# print("--- Ví dụ 3: Dùng model_dump() ---")
# print(python_dict)
# print(f"Kiểu dữ liệu trả về: {type(python_dict)}\n")


# # --- 4. Dùng model_dump_json() để chuyển thành chuỗi JSON gửi đi qua mạng ---
# json_string = item2.model_dump_json()
# print("--- Ví dụ 4: Dùng model_dump_json() ---")
# print(json_string)
# print(f"Kiểu dữ liệu trả về: {type(json_string)}")

# async def xin_chao():
#     print("Đang chạy bên trong hàm async...")
#     return "Xin chào"

# # Gọi hàm async này:
# cot = asyncio.run(xin_chao())
# print(cot)

import asyncio

# 1. Định nghĩa một tác vụ tải web bất đồng bộ
async def download_page(page_name: str, delay: int):
    print(f"--> Bắt đầu tải: {page_name}")
    
    # Giả lập việc chờ mạng mất một khoảng thời gian (dùng asyncio.sleep thay vì time.sleep)
    # Lệnh await ở đây giúp nhường quyền cho các trang khác tải cùng lúc
    await asyncio.sleep(delay) 
    
    print(f"<-- Đã tải xong: {page_name}")
    return f"Nội dung của {page_name}"

# 2. Hàm điều phối chính
async def main():
    print("=== BẮT ĐẦU CHƯƠNG TRÌNH ===")
    
    # Tạo sẵn 3 tác vụ (chưa chạy vội)
    task1 = download_page("Trang_Web_A", delay=2)
    task2 = download_page("Trang_Web_B", delay=1)
    task3 = download_page("Trang_Web_C", delay=3)
    
    # asyncio.gather giúp phóng cả 3 tác vụ này CHẠY SONG SONG CÙNG MỘT LÚC
    results = await asyncio.gather(task1, task2, task3)
    
    print("=== KẾT QUẢ THU ĐƯỢC ===")
    print(results)

# 3. Khởi động vòng lặp sự kiện của asyncio để chạy hàm main
if __name__ == "__main__":
    asyncio.run(main())