import json
import numpy as np
import google.generativeai as genai
import os
import pypdf 
from dotenv import load_dotenv

load_dotenv()

# Cấu hình API key (Hãy đảm bảo bạn đã export GEMINI_API_KEY trong terminal)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def cosine_similarity(vec_a, vec_b):
    """Tính Cosine Similarity thủ công giữa 2 vector."""
    a = np.array(vec_a)
    b = np.array(vec_b)
    # Tránh lỗi chia cho 0
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def embed_texts(texts, task_type="retrieval_document"):
    """Gọi API Gemini để nhúng mảng text thành vector."""
    result = genai.embed_content(
        model="models/gemini-embedding-2-preview",
        content=texts,
        task_type=task_type
    )
    # print("============================================================================================")
    # print(type(result))
    # print(result)
    return result['embedding']

# Thay vì import PyPDF2

def process_pdf_policy(pdf_path):
    raw_chunks = []
    try:
        with open(pdf_path, 'rb') as file:
            # Gọi trực tiếp pypdf thay vì PyPDF2
            reader = pypdf.PdfReader(file) 
            full_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            
            
            # ... phần logic chunking giữ nguyên ...
            
            # Cắt theo quy tắc: Các mục chính sách bắt đầu bằng "POL-"
            # Cách chia nhỏ (chunking) linh hoạt dựa trên cấu trúc file PDF
            paragraphs = full_text.split('POL-')
            # print("============================================================================================================================")
            # print(paragraphs[0:500])  # In ra 500 ký tự đầu để kiểm tra

            # Bỏ qua phần đầu (header/intro) không chứa "POL-"
            for i, para in enumerate(paragraphs[1:]): 
                # Khôi phục lại tiền tố "POL-" đã bị mất khi split
                full_para = "POL-" + para.strip()
                # print("==================================================")
                # print(full_para[0:500])  # In ra 500 ký tự đầu để kiểm tra
                
                
                # Tách lấy ID (ví dụ: POL-CANC-01) bằng cách lấy từ đầu tiên
                policy_id = full_para.split()[0]
                # print("==================================================")
                # print(policy_id)
                
                raw_chunks.append({
                    "id": policy_id,
                    "type": "policy",
                    "text": full_para
                })
    except Exception as e:
        print(f"[!] Lỗi khi đọc PDF: {e}")
        
    return raw_chunks

def load_data_for_embedding(policy_pdf_path, l3_results_path):
    """Đọc dữ liệu từ file chính sách PDF và kết quả JSON Lab 3, gom thành mảng chunk."""
    raw_chunks = []
    
    # 1. Xử lý file Policy PDF
    if os.path.exists(policy_pdf_path):
        print(f"[*] Đang đọc và chunking file PDF: {policy_pdf_path}...")
        policy_chunks = process_pdf_policy(policy_pdf_path)
        raw_chunks.extend(policy_chunks)
    else:
        print(f"[!] Cảnh báo: Không tìm thấy {policy_pdf_path}")

    # 2. Xử lý file l3_parsed_results.json (Đơn hàng)
    if os.path.exists(l3_results_path):
        print(f"[*] Đang đọc file kết quả Lab 3: {l3_results_path}...")
        with open(l3_results_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # print("=====================")
            # print(type(data))
            # Lấy danh sách các đơn hàng thành công
            successful_orders = data.get("successful_orders", [])
            
            for order in successful_orders:
                metadata = order.get("metadata", {})
                po_number = metadata.get('po_number', f"ORD-UNKNOWN-{id(order)}")
                customer = metadata.get('customer', 'N/A')
                order_date = metadata.get('order_date', 'N/A')
                
                # Lấy text sạch (có thể rút ngắn bớt nếu cần)
                clean_text = order.get("clean_text", "")
                
                # Tóm tắt thông tin đơn hàng
                order_text = f"Order {po_number}. Customer: {customer}. Date: {order_date}. Details: {clean_text[:500]}..." # Lấy 500 ký tự đầu để tránh vượt quá giới hạn API
                
                raw_chunks.append({
                    "id": po_number,
                    "type": "order",
                    "text": order_text
                })

    else:
        print(f"[!] Cảnh báo: Không tìm thấy {l3_results_path}")

    return raw_chunks

def build_vector_db(chunks):
    """Gửi các chunk qua API và lưu vào dictionary (RAM)."""
    if not chunks:
        return {}
        
    print(f"[*] Đang tạo embedding cho {len(chunks)} tài liệu...")
    texts = [chunk["text"] for chunk in chunks]
    embeddings = embed_texts(texts, task_type="retrieval_document")
    
    vector_db = {}
    for i, chunk in enumerate(chunks):
        vector_db[chunk["id"]] = {
            "type": chunk["type"],
            "text": chunk["text"],
            "embedding": embeddings[i] # Khớp 1:1 theo thứ tự mảng
        }
    return vector_db

def search(query, vector_db, top_k=3):
    """Tính Cosine Similarity cho truy vấn và quét toàn bộ Dictionary."""
    if not vector_db:
        return []
        
    # Nhúng câu hỏi với task_type là retrieval_query
    query_embed = embed_texts([query], task_type="retrieval_query")[0]
    
    results = []
    for chunk_id, data in vector_db.items():
        score = cosine_similarity(query_embed, data["embedding"])
        results.append({
            "id": chunk_id,
            "score": score,
            "type": data["type"],
            "text": data["text"]
        })
    
    # Sắp xếp từ cao xuống thấp
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]

if __name__ == "__main__":
    # Tên file lấy từ dữ liệu thực tế
    POLICY_FILE = "/Users/tavantai/Developer/Week1_Labs/data/Global Tech Solutions - Corporate Order Policy.pdf" 
    L3_FILE = "/Users/tavantai/Developer/Week1_Labs/src/week1_labs/l3_parsed_results.json" 
    
    # 1. Nạp và xử lý dữ liệu
    raw_chunks = load_data_for_embedding(POLICY_FILE, L3_FILE)
    
    # 2. Xây dựng hệ thống tìm kiếm trên RAM
    in_memory_db = build_vector_db(raw_chunks)
    print(f"[*] Đã lưu {len(in_memory_db)} vector vào RAM thành công!\n")
    
    # 3. Chạy test các truy vấn thực tế
    if in_memory_db:
        test_queries = [
            "refund rule for damaged goods",
            "can I cancel my order if it's already paid?",
            "how long does standard delivery take?",
            "show me details for order ORD-2026-0010"
        ]
        
        for q in test_queries:
            print("-" * 80)
            print(f"Câu hỏi: '{q}'")
            top_results = search(q, in_memory_db, top_k=2)
            
            for i, res in enumerate(top_results, 1):
                print(f"  Top {i} | ID: {res['id']} | Nhóm: {res['type'].upper()} | Khớp: {res['score']:.4f}")
                print(f"  Nội dung: {res['text']}\n")
