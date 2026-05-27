import cv2
import easyocr
import re
import unicodedata
import numpy as np
import tkinter as tk
from tkinter import messagebox

# =========================
# KHỞI TẠO AI TRƯỚC ĐỂ PHÂN LOẠI GIẤY TỜ
# =========================
image_path = 'anh_test.jpg'
output_path = 'redacted_output.jpg'

print("--- ĐANG NẠP MÔ HÌNH AI (EASYOCR)... ---")
reader = easyocr.Reader(['vi', 'en'], gpu=True)

# Đọc ảnh để quét OCR trước
img = cv2.imread(image_path)
if img is None: 
    raise FileNotFoundError(f"Không đọc được ảnh: {image_path}")

img_h, img_w = img.shape[:2]
print("🔍 AI đang phân tích loại giấy tờ để đưa ra đề xuất...")
pre_results = reader.readtext(image_path)
all_ocr_text = " ".join(
    [res[1].lower() for res in pre_results]
)
all_ocr_text = unicodedata.normalize('NFD', all_ocr_text)
all_ocr_text = "".join([ch for ch in all_ocr_text if unicodedata.category(ch) != 'Mn']) # Xóa dấu tiếng Việt

# =========================
# LOGIC AI ĐỀ XUẤT TỰ ĐỘNG
# =========================
# Khởi tạo giá trị mặc định (Tất cả bằng False)
suggested_face = False
suggested_barcode = False
suggest= False
suggested_qr = False
suggested_id_num = False
suggested_name = False
suggested_dob = False
suggested_address = False
document_type = "Không xác định (Tự chọn)"

# 1. Nếu là Căn cước công dân
if 'can cuoc' in all_ocr_text or 'citizen' in all_ocr_text:
    document_type = "Căn cước công dân (Mặt trước/sau)"
    suggested_face = True
    suggested_barcode = True
    suggest= True
    suggested_qr = True
    suggested_id_num = True
    suggested_name = True
    suggested_dob = True
    suggested_address = True

# 2. Nếu là Bảo hiểm y tế
elif 'bao hiem y te' in all_ocr_text or 'bhyt' in all_ocr_text or 'the bhyt' in all_ocr_text:
    document_type = "Thẻ Bảo hiểm y tế"
    suggested_id_num = True  # Mã số BHYT
    suggested_name = True    # Họ tên
    suggested_dob = True     # Ngày sinh
    suggested_barcode = True # Thường BHYT có mã vạch ở đáy
    # BHYT giấy không có QR, vân tay, khuôn mặt nên giữ False

# 3. Nếu là Thẻ sinh viên
elif 'sinh vien' in all_ocr_text or 'student' in all_ocr_text:
    document_type = "Thẻ sinh viên / Thẻ học sinh"
    suggested_id_num = True  # Mã số sinh viên
    suggested_name = True    # Họ tên
    suggested_barcode = True # Mã vạch thẻ thư viện
    suggested_face = True    # Ảnh chân dung sinh viên

print(f"📌 AI ĐỀ XUẤT: Loại giấy tờ phát hiện được là -> [{document_type}]")

# =========================
# GIAO DIỆN HIỂN THỊ ĐỀ XUẤT
# =========================
def get_user_preferences():
    """Hàm bật cửa sổ menu đã được AI tick sẵn các ô phù hợp"""
    root = tk.Tk()
    root.title("Hệ thống che thông tin thông minh")
    root.geometry("460x500")
    root.configure(bg="#F0F7F4")

    # --- NẠP CÁC GIÁ TRỊ ĐÃ ĐƯỢC AI ĐỀ XUẤT VÀO BIẾN ---
    var_face = tk.BooleanVar(value=suggested_face)
    var_barcode = tk.BooleanVar(value=suggested_barcode)
    var_finger = tk.BooleanVar(value=suggest)
    var_qr = tk.BooleanVar(value=suggested_qr)

    var_id_num = tk.BooleanVar(value=suggested_id_num)    
    var_name = tk.BooleanVar(value=suggested_name)      
    var_dob = tk.BooleanVar(value=suggested_dob)       
    var_address = tk.BooleanVar(value=suggested_address)   

    # Hiển thị loại giấy tờ AI nhận diện được lên giao diện
    tk.Label(root, text=f"🔍 AI nhận diện: {document_type}", bg="#E8F1F5", fg="#1D3557", font=("Arial", 11, "italic"), bd=1, relief="solid", padx=10, pady=5).pack(fill="x", padx=30, pady=(15, 5))
    tk.Label(root, text="🛠️ BẠN CÓ THỂ ĐIỀU CHỈNH LẠI NẾU MUỐN:", bg="#F0F7F4", fg="#2C3E50", font=("Arial", 11, "bold")).pack(pady=5)

    # Khung nhóm 1: Phần hình ảnh & Vật lý
    f1 = tk.LabelFrame(root, text=" Vùng hình ảnh & Mã vạch ", bg="#F0F7F4", font=("Arial", 10, "bold"), padx=10, pady=5)
    f1.pack(fill="x", padx=30, pady=5)
    tk.Checkbutton(f1, text="Che khuôn mặt (Chân dung)", variable=var_face, bg="#F0F7F4", font=("Arial", 10)).pack(anchor="w", padx=20)
    tk.Checkbutton(f1, text="Che mã vạch (Barcode)", variable=var_barcode, bg="#F0F7F4", font=("Arial", 10)).pack(anchor="w", padx=20)
    tk.Checkbutton(f1, text="Che dấu vân tay", variable=var_finger, bg="#F0F7F4", font=("Arial", 10)).pack(anchor="w", padx=20)
    tk.Checkbutton(f1, text="Che mã QR", variable=var_qr, bg="#F0F7F4", font=("Arial", 10)).pack(anchor="w", padx=20)

    # Khung nhóm 2: Phần văn bản chữ
    f2 = tk.LabelFrame(root, text=" Thông tin văn bản (Chữ) ", bg="#F0F7F4", font=("Arial", 10, "bold"), padx=10, pady=5)
    f2.pack(fill="x", padx=30, pady=5)
   # Khung nhóm 2: Phần văn bản chữ
    f2 = tk.LabelFrame(root, text=" Thông tin văn bản (Chữ) ", bg="#F0F7F4", font=("Arial", 10, "bold"), padx=10, pady=5)
    f2.pack(fill="x", padx=30, pady=5)
    
    # SỬA SỐ 2 THÀNH f2 Ở ĐÂY:
    tk.Checkbutton(f2, text="Che Số giấy tờ (Số định danh/Số thẻ)", variable=var_id_num, bg="#F0F7F4", font=("Arial", 10)).pack(anchor="w", padx=20)
    tk.Checkbutton(f2, text="Che Họ và tên", variable=var_name, bg="#F0F7F4", font=("Arial", 10)).pack(anchor="w", padx=20)
    tk.Checkbutton(f2, text="Che Ngày tháng năm sinh", variable=var_dob, bg="#F0F7F4", font=("Arial", 10)).pack(anchor="w", padx=20)
    tk.Checkbutton(f2, text="Che Địa chỉ (Quê quán, Thường trú)", variable=var_address, bg="#F0F7F4", font=("Arial", 10)).pack(anchor="w", padx=20)

    prefs = {}

    def on_submit():
        prefs['face'] = var_face.get()
        prefs['barcode'] = var_barcode.get()
        prefs['finger'] = var_finger.get()
        prefs['qr'] = var_qr.get()
        
        prefs['id_num'] = var_id_num.get()
        prefs['name'] = var_name.get()
        prefs['dob'] = var_dob.get()
        prefs['address'] = var_address.get()
        root.destroy()

    tk.Button(root, text="Xác nhận và Xử lý ảnh", command=on_submit, bg="#A8DADC", fg="#1D3557", font=("Arial", 11, "bold"), padx=25, pady=5, cursor="hand2").pack(pady=15)

    root.mainloop()
    return prefs

# --- THỰC THI MENU ---
user_choices = get_user_preferences()

if not user_choices:
    print("Đã hủy thao tác xử lý ảnh.")
    exit()

# Cấu hình bật tắt động theo người dùng chọn (Được AI đề xuất sẵn trước đó)
REDACT_FACE_AREA = user_choices['face']
REDACT_BARCODE = user_choices['barcode']
REDACT_FINGERPRINT = user_choices['finger']
REDACT_QR_CODE = user_choices['qr']

# Tạo danh sách từ khóa động dựa trên ô tick của người dùng
sensitive_keywords = []
multi_line_keywords = []
next_line_keywords = []
vietnam_address_words = []

# Đề xuất bổ sung từ khóa động phù hợp với BHYT / CCCD / Thẻ sinh viên
if user_choices['id_num']:
    # Thêm cả các từ khóa của BHYT như 'ma so', 'so the bhyt'
    sensitive_keywords.extend(['so', 'so the', 'so cccd', 'so ho chieu', 'ma so thue', 'mst', 'so bhxh', 'so bhyt', 'ma so', 'ma the', 'no'])

if user_choices['name']:
    sensitive_keywords.extend(['ho va ten', 'ho ten', 'ten', 'full name', 'name', 'ho ten:'])
    next_line_keywords.extend(['ho va ten', 'ho ten', 'full name', 'name'])

if user_choices['dob']:
    sensitive_keywords.extend(['ngay sinh', 'sinh ngay', 'date of birth', 'dob', 'ngay cap', 'date of issue', 'ngay het han', 'co gia tri den', 'expiry', 'valid until', 'nam sinh:'])
    next_line_keywords.extend(['ngay sinh', 'date of birth', 'ngay cap', 'ngay het han', 'expiry', 'co gia tri den'])

if user_choices['address']:
    sensitive_keywords.extend(['que quan', 'place of origin', 'noi sinh', 'place of birth', 'noi thuong tru', 'thuong tru', 'place of residence', 'residence', 'dia chi', 'address', 'noi o hien tai', 'noi dki kcb ban dau', 'noi dk kcb'])
    multi_line_keywords.extend(['que quan', 'place of origin', 'noi sinh', 'place of birth', 'noi thuong tru', 'thuong tru', 'place of residence', 'residence', 'dia chi', 'address', 'noi o hien tai', 'noi dki kcb ban dau'])
    vietnam_address_words.extend(['tp hcm', 'tphcm', 'ho chi minh', 'ha noi', 'da nang', 'can tho', 'hai phong', 'binh duong', 'dong nai', 'long an', 'ba ria', 'vung tau', 'quan', 'huyen', 'thi xa', 'thanh pho', 'phuong', 'xa', 'thi tran', 'ap', 'thon', 'khu pho', 'duong', 'so nha'])

sensitive_keywords.extend(['dac diem nhan dang', 'personal identification', 'nhan dang'])
multi_line_keywords.extend(['dac diem nhan dang', 'personal identification'])

FACE_AREA_RATIO = {
    "x1": 0.03, "y1": 0.4, "x2": 0.30, "y2": 0.82,
}

# =========================
# HÀM HỖ TRỢ
# =========================

def remove_accents(text):
    text = unicodedata.normalize('NFD', text)
    text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')
    return text

def normalize_text(text):
    text = remove_accents(text)
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def has_keyword(norm_text, keywords):
    for kw in keywords:
        if re.search(r'\b' + re.escape(kw) + r'\b', norm_text):
            return True
    return False

def get_rect_from_bbox(bbox):
    xs = [point[0] for point in bbox]
    ys = [point[1] for point in bbox]
    return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))

def redact_rect(img, x1, y1, x2, y2, padding=2):
    img_h, img_w = img.shape[:2]
    x1 = max(0, int(x1) - padding)
    y1 = max(0, int(y1) - padding)
    x2 = min(img_w, int(x2) + padding)
    y2 = min(img_h, int(y2) + padding)
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), -1)

def pixelate_region(img, x1, y1, x2, y2, blocks=12):
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(img.shape[1], int(x2)), min(img.shape[0], int(y2))
    roi = img[y1:y2, x1:x2]
    if roi.size == 0:
        return
    h, w = roi.shape[:2]
    temp = cv2.resize(roi, (blocks, blocks), interpolation=cv2.INTER_LINEAR)
    pixelated = cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)
    img[y1:y2, x1:x2] = pixelated

def merge_nearby_boxes(boxes, distance=5):
    if not boxes: return []
    merged = []
    used = [False] * len(boxes)
    for i in range(len(boxes)):
        if used[i]: continue
        x1, y1, x2, y2 = boxes[i]
        used[i] = True
        changed = True
        while changed:
            changed = False
            for j in range(len(boxes)):
                if used[j]: continue
                xx1, yy1, xx2, yy2 = boxes[j]
                if (xx1 <= x2 + distance and xx2 >= x1 - distance and 
                    yy1 <= y2 + distance and yy2 >= y1 - distance):
                    x1, y1 = min(x1, xx1), min(y1, yy1)
                    x2, y2 = max(x2, xx2), max(y2, yy2)
                    used[j] = True
                    changed = True
        merged.append((x1, y1, x2, y2))
    return merged

def line_has_sensitive_pattern(text):
    compact_text = re.sub(r'\s+', '', text)
    digits_only = re.sub(r'\D', '', text)
    
    # --- 1. NẾU NGƯỜI DÙNG CHỌN CHE SỐ ĐỊNH DANH (ID Number) ---
    if user_choices['id_num']:
        # Bắt CMND 9 số, CCCD 12 số
        if re.search(r'(?:\d[\s.-]?){12}', text) or re.search(r'(?:\d[\s.-]?){9}', text):
            return True
        # Bắt thẻ BHYT (2 chữ + 10 số) hoặc Hộ chiếu (1 chữ + 7/8 số)
        if re.search(r'[a-zA-Z]{2}\d{10}', compact_text) or re.search(r'[A-Z]\d{7,8}', compact_text):
            return True
        # Bắt mã số định danh khác (10-13 số liền nhau)
        if re.search(r'\d{10,13}', compact_text):
            return True
        # Bẫy số độc lập (Chỉ bắt dòng có ĐÚNG 9 hoặc 12 chữ số, loại bỏ nhiễu rác OCR)
        if len(digits_only) in [9, 12]:
            return True

    # --- 2. NẾU NGƯỜI DÙNG CHỌN CHE NGÀY THÁNG NĂM SINH ---
    if user_choices['dob']:
        # Bắt định dạng chuẩn: 22/10/2006 hoặc 2006-10-22
        if re.search(r'\d{2}[\/\-.]\d{2}[\/\-.]\d{4}', text) or re.search(r'\d{4}[\/\-.]\d{2}[\/\-.]\d{2}', text):
            return True

    return False

# =========================
# SỬ DỤNG LẠI KẾT QUẢ OCR ĐỂ GOM DÒNG VÀ VẼ CHE
# =========================
# Sắp xếp các kết quả đã quét từ trước
ocr_items = []
print("\n===== NỘI DUNG OCR =====")
for bbox, text, conf in pre_results:
    text = text.strip()
    if not text: continue
    x1, y1, x2, y2 = get_rect_from_bbox(bbox)
    item = {
        'text': text, 'norm_text': normalize_text(text), 'conf': conf,
        'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
        'center_y': (y1 + y2) // 2, 'height': y2 - y1,
    }
    ocr_items.append(item)
    print(text)

ocr_items = sorted(ocr_items, key=lambda item: (item['y1'], item['x1']))

lines = []
for item in ocr_items:
    added = False
    for line in lines:
        avg_height = max(12, item['height'])
        if abs(item['center_y'] - line['center_y']) < max(18, avg_height * 0.7):
            line['items'].append(item)
            line['center_y'] = sum([i['center_y'] for i in line['items']]) // len(line['items'])
            added = True
            break
    if not added: lines.append({'center_y': item['center_y'], 'items': [item]})

line_items = []
for line in lines:
    items = sorted(line['items'], key=lambda item: item['x1'])
    line_text = ' '.join(item['text'] for item in items)
    norm_line_text = normalize_text(line_text)
    line_items.append({
        'text': line_text, 'norm_text': norm_line_text,
        'x1': min(i['x1'] for i in items), 'y1': min(i['y1'] for i in items),
        'x2': max(i['x2'] for i in items), 'y2': max(i['y2'] for i in items),
        'center_y': (min(i['y1'] for i in items) + max(i['y2'] for i in items)) // 2,
        'height': max(i['y2'] for i in items) - min(i['y1'] for i in items),
        'items': items,
    })

line_items = sorted(line_items, key=lambda item: item['y1'])
safe_phrases = [
    'cong hoa xa hoi chu nghia viet nam', 'cong hoa xa hoi', 'chu nghia viet nam',
    'doc lap tu do hanh phuc', 'doc lap tu do', 'hanh phuc',
    'can cuoc cong dan', 'citizen identity card', 'can cuoc', 'identity card',
    'giam doc cong an', 'cuc truong cuc',
]

def is_safe_phrase(norm_text):
    for safe in safe_phrases:
        if safe in norm_text: return True
    return False
redact_boxes = []
for index, line in enumerate(line_items):
    is_sensitive = False
    norm = line['norm_text']
    text = line['text']
    
    if is_safe_phrase(norm) and not line_has_sensitive_pattern(text): continue
    if line_has_sensitive_pattern(text): is_sensitive = True
    if has_keyword(norm, sensitive_keywords): is_sensitive = True
    if has_keyword(norm, vietnam_address_words) and len(norm) >= 8: is_sensitive = True

    if has_keyword(norm, multi_line_keywords):
        for j in range(index + 1, min(index + 5, len(line_items))):
            redact_boxes.append((line_items[j]['x1'], line_items[j]['y1'], line_items[j]['x2'], line_items[j]['y2']))

    if has_keyword(norm, next_line_keywords):
        for j in range(index + 1, min(index + 2, len(line_items))):  # bắt đầu từ dòng SAU
            redact_boxes.append((line_items[j]['x1'], line_items[j]['y1'], line_items[j]['x2'], line_items[j]['y2']))

    if is_sensitive:
        colon_x = None
        for it in sorted(line['items'], key=lambda i: i['x1']):
            if ':' in it['text']:
                colon_x = it['x2']
                break
    
        if colon_x:
            redact_boxes.append((colon_x, line['y1'], line['x2'], line['y2']))
        else:
            redact_boxes.append((line['x1'], line['y1'], line['x2'], line['y2']))

# for item in ocr_items:
#     norm = item['norm_text']
#     if is_safe_phrase(norm) and not line_has_sensitive_pattern(item['text']): continue
#     if has_keyword(norm, sensitive_keywords):
#         redact_boxes.append((item['x1'], item['y1'], item['x2'], item['y2']))

expanded_boxes = []
for x1, y1, x2, y2 in redact_boxes:
    expanded_boxes.append((max(0, x1 - 5), max(0, y1 - 3), min(img_w, x2 + 5), min(img_h, y2 + 3)))

for x1, y1, x2, y2 in expanded_boxes:
    redact_rect(img, x1, y1, x2, y2, padding=0)

# =========================
# CÁC LỚP MỜ HÌNH ẢNH (CHỈ CHẠY NẾU ĐƯỢC CHỌN)
# =========================
if REDACT_QR_CODE:
    qr_anchors = ['can cuoc cong dan', 'citizen identity card', 'can cuoc']
    for line in line_items:
        if any(anchor in line['norm_text'] for anchor in qr_anchors):
            x1, y1, x2, y2 = line['x1'], line['y1'], line['x2'], line['y2']
            h_text = y2 - y1
            qr_x1 = x2 + int(h_text * 0.3)
            qr_y1 = y1 - int(h_text * 2.0)
            qr_size = int(h_text * 3.0) 
            pixelate_region(img, qr_x1, qr_y1, min(img.shape[1], qr_x1 + qr_size), min(img.shape[0], qr_y1 + qr_size), blocks=12)
            break 

if REDACT_FINGERPRINT:
    left_anchors = ['ngon tro trai', 'left index', 'tro trai']
    right_anchors = ['ngon tro phai', 'right index', 'tro phai']
    left_finger_boxes, right_finger_boxes = [], []
    for item in ocr_items:
        norm = item['norm_text']
        x1, y1, x2, y2 = item['x1'], item['y1'], item['x2'], item['y2']
        h_text = y2 - y1
        box_data = {'x1': max(0, x1 - int(h_text * 1.5)), 'y1': max(0, y1 - int(h_text * 9)), 'x2': min(img.shape[1], x2 + int(h_text * 1.5)), 'y2': max(0, y1 - 2), 'text': item['text']}
        if any(a in norm for a in left_anchors): left_finger_boxes.append(box_data)
        elif any(a in norm for a in right_anchors): right_finger_boxes.append(box_data)

    final_left_boxes = []
    if left_finger_boxes and right_finger_boxes:
        ref_y1, ref_y2 = right_finger_boxes[0]['y1'], right_finger_boxes[0]['y2']
        for left in left_finger_boxes: final_left_boxes.append({'x1': left['x1'], 'y1': ref_y1, 'x2': left['x2'], 'y2': ref_y2})
    else: final_left_boxes = left_finger_boxes

    for right in right_finger_boxes: pixelate_region(img, right['x1'], right['y1'], right['x2'], right['y2'], blocks=8)
    for left in final_left_boxes: pixelate_region(img, left['x1'], left['y1'], left['x2'], left['y2'], blocks=8)

if REDACT_FACE_AREA: 
    # Tự động tìm khuôn mặt bằng Cascade
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    gray_face = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    for (x, y, w, h) in face_cascade.detectMultiScale(gray_face, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)):
         pixelate_region(img, x, y, x + w, y + h, blocks=8)
    # Tỉ lệ cố định phòng hờ
    f_x1, f_y1 = int(img_w * FACE_AREA_RATIO["x1"]), int(img_h * FACE_AREA_RATIO["y1"])
    f_x2, f_y2 = int(img_w * FACE_AREA_RATIO["x2"]), int(img_h * FACE_AREA_RATIO["y2"])
    pixelate_region(img, f_x1, f_y1, f_x2, f_y2, blocks=10)

cv2.imwrite(output_path, img)
print(f"\n✨ Xử lý hoàn tất! Đã lưu ảnh tại: {output_path}")