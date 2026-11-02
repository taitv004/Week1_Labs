# Phân tích kỹ thuật & Giới hạn của hệ thống Naive Order-Policy Search (Lab 5)

Dựa trên kết quả thực thi thực tế (log output) của script `l5_naive_search.py`, hệ thống "tìm kiếm ngữ nghĩa ngây thơ" hoạt động hoàn hảo cho các câu hỏi mang tính khái niệm, nhưng bộc lộ những điểm yếu chí mạng khi đối mặt với dữ liệu định danh và hiệu suất tính toán.

Dưới đây là 4 điểm "gãy" (breaking points) cốt lõi nếu đưa kiến trúc này vào môi trường thực tế (Production):

## 1. Điểm mù của Vector Search: Ngữ nghĩa (Semantic) vs. Từ khóa chính xác (Lexical)

**Log thực tế ghi nhận lỗi:**
* Truy vấn: `'show me details for order ORD-2026-0010'`
* Top 1 trả về: `ORD-2026-0003` (Độ khớp: **0.7289**) ❌
* Top 2 trả về: `ORD-2026-0010` (Độ khớp: **0.7222**) ✅

**Phân tích nguyên nhân:**
Mô hình embedding (`text-embedding-004`) biến đổi văn bản thành một tọa độ không gian nhiều chiều dựa trên **ý nghĩa tổng thể**, không phải để đếm từ khóa.
* Câu hỏi mang ý nghĩa: *"Tôi muốn xem chi tiết một đơn hàng"*.
* Hệ thống quét qua các văn bản và thấy tất cả các đơn hàng đều có cấu trúc chữ tương tự nhau (`PURCHASE ORDER... Customer... Total...`).
* Về mặt toán học, đơn hàng số `0003` vô tình chứa tập hợp từ vựng có phân bố vector gần với câu hỏi hơn một chút xíu (0.7289 > 0.7222) so với đơn hàng `0010`. Sự khác biệt của một mã ID (`0003` vs `0010`) bị "pha loãng" trong không gian 768 chiều.

**Cách khắc phục thực tế:**
Không bao giờ dùng Vector Search để tìm Exact ID. Hệ thống thực tế phải dùng **Hybrid Search** (Tìm kiếm lai):
* Dùng Text Search truyền thống (hoặc Metadata Filtering trong Vector DB) để ép điều kiện `WHERE id = 'ORD-2026-0010'` (Lexical search).
* Chỉ dùng Vector Search cho các câu hỏi chính sách mở (như `"refund rule"`).

## 2. Nút thắt cổ chai về độ phức tạp thuật toán: O(N) Time Complexity

**Log thực tế:**
* Hệ thống tính toán trơn tru và báo cáo `Đã lưu 32 vector vào RAM thành công!`.

**Phân tích nguyên nhân:**
Hiện tại hệ thống tính Cosine Similarity bằng vòng lặp `for` quét qua từng vector một. Đối với 32 tài liệu, thời gian xử lý là tính bằng mili-giây. Tuy nhiên, thuật toán này có độ phức tạp là `O(N)`. 
Nếu một doanh nghiệp có 5 triệu đơn hàng (N = 5,000,000), mỗi một câu hỏi của khách hàng sẽ kích hoạt 5 triệu phép nhân ma trận.

**Cách khắc phục thực tế:**
Cần sử dụng các thuật toán **ANN (Approximate Nearest Neighbors)** như HNSW (Hierarchical Navigable Small World) hoặc IVF (Inverted File Index) được tích hợp sẵn trong các Vector Database chuyên nghiệp, giúp giảm thời gian tìm kiếm xuống `O(log N)` (tìm trong hàng triệu record chỉ mất vài chục mili-giây).

## 3. Tràn bộ nhớ (Memory Exhaustion) và Tính bay hơi (Volatility)

**Log thực tế:**
* Hệ thống lưu trữ dữ liệu dưới dạng `in_memory_db = build_vector_db(...)`.

**Phân tích nguyên nhân:**
Mỗi vector từ Gemini có 768 chiều (tương đương khoảng 3KB mỗi vector nếu dùng float32). Lưu trữ 32 vector mất khoảng 100KB, rất an toàn. Nhưng nếu lưu trữ 10 triệu văn bản, nó sẽ "ngốn" hàng chục GB RAM vật lý.
Hơn nữa, vì nằm trên RAM, mỗi lần script tắt, toàn bộ dữ liệu sẽ bốc hơi. Lần chạy sau lại tốn tiền gọi API Gemini để nhúng lại từ đầu.

**Cách khắc phục thực tế:**
Sử dụng **Vector Database có khả năng lưu trữ xuống ổ cứng (Disk-backed)** và quản lý RAM thông minh như ChromaDB, Qdrant, hoặc Pinecone.

## 4. Nợ kỹ thuật (Technical Debt) & Lỗi thư viện lỗi thời

**Log thực tế ghi nhận cảnh báo:**
* `FutureWarning: All support for the 'google.generativeai' package has ended. Please switch to 'google.genai'`

**Phân tích nguyên nhân:**
Google đã phát hành SDK mới (`google-genai`) với kiến trúc khác biệt hoàn toàn. Việc tiếp tục sử dụng thư viện cũ (`google.generativeai`) cho bài toán Production sẽ dẫn đến việc hệ thống không nhận được bản vá bảo mật và sẽ bị ngừng hoạt động đột ngột khi API cũ bị tắt.

**Cách khắc phục thực tế:**
Bắt buộc nâng cấp base code sang SDK mới nhất trong môi trường thực tế để đảm bảo hệ thống duy trì được độ ổn định (Stability).