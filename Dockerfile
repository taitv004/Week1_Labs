# Sử dụng base image Python chính thức, gọn nhẹ
FROM python:3.12-slim

# Thiết lập thư mục làm việc bên trong container
WORKDIR /app

# Cài đặt công cụ quản lý gói uv
RUN pip install --no-cache-dir uv

# Copy toàn bộ mã nguồn và file pyproject.toml vào container
COPY . /app/

# Cài đặt mã nguồn và đồng thời cài thêm pytest, httpx trực tiếp vào hệ thống Python
RUN uv pip install --system -e . && uv pip install --system pytest httpx

# Mở cổng 8000 để truy cập API từ bên ngoài
EXPOSE 8000

# Lệnh khởi động ứng dụng FastAPI
CMD ["uvicorn", "week1_labs.l4_api:app", "--host", "0.0.0.0", "--port", "8000"]