# DBH-EHR AI Chatbot System (v7.0 - Supabase Cloud Edition)

Hệ thống Trợ lý AI tích hợp vào Bệnh án điện tử DBH, hỗ trợ **đặt lịch khám**, **xem và hủy lịch hẹn**, **tra cứu bệnh án** và **chính sách bệnh viện** thông qua giao tiếp ngôn ngữ tự nhiên. 
Kiến trúc ở phiên bản mới nhất đã tối ưu hóa hiệu năng, gỡ bỏ các LLM Local dư thừa và nâng cấp lưu trữ lên Database Đám mây.

---

## 🏗️ Kiến trúc Mới (Cloud-Native)

```
Người dùng (ChatbotWidget)
        │
        ▼
  Next.js Frontend  ──►  /api/chatbot  (proxy)
        │
        ▼
   n8n Workflow  (LightRAG_Chatbot_Workflow.json)
   ├── Phân loại intent (OpenRouter / GPT-4o-mini)
   ├── Đặt / Xem / Hủy lịch  ──►  C# Backend API (Gateway :5000)
   ├── Tra cứu bệnh án        ──►  C# Backend API (Gateway :5000)
   └── Hỏi chính sách         ──►  LightRAG Server (:9621)
```

**Các Nâng cấp Core API:**
- **Vector Storage:** Đã chuyển đổi từ tệp Local sang CSDL đám mây **Supabase (PostgreSQL)** (Sử dụng `PGVectorStorage`, `PGKVStorage`).
- **Embeddings:** Sử dụng **API Embeddings của OpenAI (`text-embedding-3-small`)** qua mạng cực nhanh thay vì tải model `sentence-transformers` hàng trăm MB.
- **Quyền Truy cập (RBAC):** Quản lý qua tệp trỏ tài liệu chung (`rbac_mappings.json`).

---

## ✨ Tính năng

| Tính năng | Mô tả |
|---|---|
| 🗓️ **Đặt lịch khám** | Tìm bác sĩ theo chuyên khoa → chọn ngày → chọn giờ → xác nhận |
| 📋 **Xem lịch hẹn** | Hiển thị danh sách lịch đang hoạt động, click để xem chi tiết |
| 🚫 **Hủy lịch** | Hủy lịch PENDING/CONFIRMED với bước xác nhận 2 lần |
| 🩺 **Tra cứu bệnh án** | Xem hồ sơ EHR cá nhân (chỉ bệnh nhân đã đăng nhập) |
| 📄 **Hỏi chính sách** | Truy vấn nội quy, quy trình bệnh viện qua LightRAG |
| 🔐 **Phân quyền Động** | Tài liệu Knowledge Base tách biệt động dựa trên Role của token truy vấn |

---

## 📁 Cấu trúc thư mục

```
light-rag-DBH-system/
├── LightRAG_Chatbot_Workflow.json   # Workflow n8n (import vào localhost:5678)
├── admin_rabc_manager.html          # UI Quản lý tài liệu Role-based mini
└── knowledge_base/
    ├── rag_server.py                # FastApi Server phục vụ RAG (port 9621)
    ├── index_docs.py                # Script Index tài liệu đẩy lên Supabase
    ├── rbac_mappings.json           # File gốc điều hướng Document ↔ Role
    ├── docs/                        # Tài liệu nạp (markdown)
    └── rag_storage_<role>           # Local Hash Caches (chỉ cache, data gốc ở Supabase)
```

---

## 🚀 Khởi động (Cách tích hợp)

### Cách 1 — Chạy Auto cùng Hệ sinh thái (Khuyến nghị)
LightRAG đã được tích hợp chặt chẽ vào `docker-compose.dev.yml` của repository gốc **DBH-EHR-System**.
Trong quá trình build, Docker sẽ tự động:
1. Liên kết API Keys.
2. Chạy hàm index để đồng bộ dữ liệu với Supabase.
3. Kích hoạt endpoint FastApi.

Chỉ cần gõ:
```bash
# Từ thư mục gốc mạng DBH-EHR-System
docker compose -f docker-compose.dev.yml up -d
```

### Cách 2 — Chạy thủ công (Test Dev)
```bash
cd knowledge_base
pip install "lightrag-hku[api]" openai asyncpg numpy
python index_docs.py    # Dọn dẹp Database Cloud và Index lại
python rag_server.py    # Khởi động FastApi
```

---

## 📚 Quản lý Tài liệu Knowledge Base

Việc quản lý tài liệu đã trở nên linh hoạt hơn rất nhiều thông qua cơ chế Mapping:

1. **Thêm file nội dung:** Đuôi `.md` tại `knowledge_base/docs/`.
2. **Khai báo phân quyền:** Điền tên file và quyền xem vào `knowledge_base/rbac_mappings.json`. Ví dụ:
   ```json
   {
      "rules.md": ["patient", "admin", "doctor"],
      "secret-finance.md": ["admin"]
   }
   ```
3. **Cập nhật lên Supabase:**
   Từ Frontend Admin hoặc Postman, gọi API: 
   `POST http://localhost:9621/api/kb/reindex`

---

## 🔗 Endpoints liên quan

| Service | Interface |
|---|---|
| Server Health | `GET http://localhost:9621/health` |
| Truy vấn (n8n dùng) | `POST http://localhost:9621/query` |
| Quản lý Docs | `GET / POST / DELETE /api/kb/documents` |
| Trigger Đồng bộ | `POST http://localhost:9621/api/kb/reindex` |
