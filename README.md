# SocialHub split dùng logic test1.py

Cấu trúc:

```text
socialhub_split_test1_logic/
├── main.py                    # chỉ connect UI + logic
├── socialhub_ui.py            # giao diện SocialHub Soft UI
├── socialhub_logic.py         # logic social app + hàm connect tới test1
└── test1_redaction_logic.py   # logic xử lý ảnh lấy từ test1.py
```

Chạy app:

```bash
python3 main.py
```

## Điểm quan trọng

`main.py` không tạo giao diện nữa. Nó chỉ connect:

```python
init_db()
logic = SocialAppLogic()
SocialHubUI(root, logic)
```

Khi bạn tick `Che dữ liệu bằng AI`, `socialhub_logic.py` sẽ gọi `test1_redaction_logic.py`.

Vì `test1.py` cũ dùng hard-code:

```python
image_path = 'anh_test.jpg'
output_path = 'redacted_output.jpg'
```

nên `socialhub_logic.py` sẽ:
1. copy ảnh bạn chọn thành `anh_test.jpg` trong thư mục tạm
2. chạy `test1_redaction_logic.py`
3. lấy `redacted_output.jpg`
4. đưa ảnh đã xử lý vào bài đăng/chat

## Cài thư viện AI nếu muốn dùng chức năng che ảnh

```bash
pip install opencv-python easyocr vietocr torch torchvision numpy pillow
```
