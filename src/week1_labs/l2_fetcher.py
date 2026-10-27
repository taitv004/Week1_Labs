import asyncio
import logging
import httpx
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Khởi tạo Semaphore giới hạn 5 request đồng thời
SEMAPHORE_LIMIT = 5
semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)

# 1. Pydantic Models
class OrderItem(BaseModel):
    productId: int
    quantity: int = Field(ge=1)
    unitPrice: float = Field(gt=0)

class Order(BaseModel):
    id: int | str
    customerName: str
    lines: List[OrderItem]
    total: float
    status: str = "PENDING_PAYMENT"

# 2. Hàm Worker độc lập lấy và xác thực 1 đơn hàng
async def fetch_single_order(client: httpx.AsyncClient, order_id: int) -> Optional[Order]:
    url = f"http://localhost:3000/orders/{order_id}"
    
    async with semaphore:
        try:
            response = await client.get(url, timeout=5.0)
            response.raise_for_status()
            
            raw_data = response.json()
            
            validated_order = Order.model_validate(raw_data)
            
            logger.info(f"Thành công: Đơn hàng {order_id} của khách '{validated_order.customerName}' hợp lệ.")
            return validated_order

        except httpx.TimeoutException:
            logger.error(f"Timeout ở đơn hàng ID: {order_id}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Lỗi HTTP ở đơn hàng {order_id}: {e.response.status_code}")
        except ValidationError as e:
            logger.warning(f"Dữ liệu bẩn ở đơn hàng {order_id}: {e}")
        except Exception as e:
            logger.error(f"Lỗi không xác định ở đơn hàng {order_id}: {e}")
            
        return None

# 3. Hàm điều phối tổng thể (Có thể gọi từ bên ngoài module khác)
async def fetch_all_orders(order_ids: List[int]) -> List[Order]:
    start_time = asyncio.get_event_loop().time()
    
    async with httpx.AsyncClient() as client:
        tasks = [fetch_single_order(client, oid) for oid in order_ids]
        results = await asyncio.gather(*tasks)
        
    end_time = asyncio.get_event_loop().time()
    
    # Lọc bỏ các kết quả None (dữ liệu lỗi hoặc hỏng)
    valid_orders = [res for res in results if res is not None]
    
    logger.info("=" * 40)
    logger.info(f"TỔNG KẾT TIẾN TRÌNH L2:")
    logger.info(f"- Tổng số request đã gửi: {len(order_ids)}")
    logger.info(f"- Số đơn hàng hợp lệ vượt qua Pydantic: {len(valid_orders)}")
    logger.info(f"- Tổng thời gian chạy đồng thời: {end_time - start_time:.4f} giây")
    logger.info("=" * 40)
    
    return valid_orders

if __name__ == "__main__":
    # Điểm chạy thử nghiệm độc lập (Entry point)
    ids_to_fetch = list(range(1, 50))
    asyncio.run(fetch_all_orders(ids_to_fetch))