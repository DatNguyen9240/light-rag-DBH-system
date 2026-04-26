# CHÍNH SÁCH QUẢN TRỊ HỆ THỐNG (CHỈ DÀNH CHO ADMIN)

## 1. Chính sách Quản lý người dùng:
- Hỏi: "Ai có quyền kích hoạt hoặc vô hiệu hóa tài khoản?" -> Đáp: Bất kỳ Quản trị viên (Admin) nào cũng có quyền kích hoạt hoặc vô hiệu hóa bất kỳ tài khoản nào trong hệ thống.
- Hỏi: "Có quy định gì về mật khẩu không?" -> Đáp: Mật khẩu mặc định của người dùng mới không được phép sử dụng quá 24h.
- Hỏi: "Admin có tự ý reset mã OTP không?" -> Đáp: Admin chỉ thực hiện việc reset mã OTP theo yêu cầu trực tiếp từ cấp quản lý.

## 2. Chính sách Bảo trì Database:
- Hỏi: "Admin thiết lập lịch backup định kỳ như thế nào?" -> Đáp: Cần thiết lập lịch backup định kỳ vào lúc 02:00 sáng mỗi ngày.
- Hỏi: "Tôi có thể xóa bản ghi ehr_records không?" -> Đáp: Tuyệt đối Không được phép thực hiện truy vấn DELETE trực tiếp trên bảng `ehr_records` nếu không có văn bản phê duyệt.

## 3. Chính sách Quản lý Key Blockchain:
- Hỏi: "Lưu khóa riêng tư ở đâu?" -> Đáp: Tất cả Private Key trong hệ thống phải được mã hóa và lưu trữ an toàn trong Vault.
- Hỏi: "Ai có quyền truy cập Key Blockchain?" -> Đáp: Chỉ những người đại diện pháp luật mới có quyền yêu cầu Admin truy xuất các Key này.

HƯỚNG DẪN DÀNH CHO QUẢN TRỊ VIÊN (ADMIN)