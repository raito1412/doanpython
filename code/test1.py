import cv2
import easyocr
import re
import unicodedata
import numpy as np
import tkinter as tk
from tkinter import messagebox
import argparse
import os


# =========================
# NHẬN TÊN ẢNH TỪ LỆNH CHẠY
# =========================
def parse_args():
    parser = argparse.ArgumentParser(
        description="Che thông tin nhạy cảm trên ảnh giấy tờ/CV."
    )
    parser.add_argument(
        "image",
        nargs="?",
        default="anh_test.jpg",
        help="Tên file ảnh đầu vào. Ví dụ: python3 test1.py anh_test.png"
    )
    parser.add_argument(
        "-o", "--output",
        default="redacted_output.jpg",
        help="Tên file ảnh sau khi che. Mặc định: redacted_output.jpg"
    )

    # Hỗ trợ trường hợp bạn gõ nhầm dạng: python3 test1.py --anh_test.png
    # argparse sẽ hiểu đây là option lạ, nên mình lấy lại và xem nó như tên ảnh.
    args, unknown = parser.parse_known_args()
    if unknown and args.image == "anh_test.jpg":
        possible_image = unknown[0]
        if possible_image.startswith("--"):
            possible_image = possible_image[2:]
        elif possible_image.startswith("-"):
            possible_image = possible_image[1:]
        args.image = possible_image

    return args

args = parse_args()
image_path = args.image
output_path = args.output

if not os.path.exists(image_path):
    raise FileNotFoundError(
        f"Không tìm thấy ảnh: {image_path}. "
        f"Cách chạy đúng: python3 test1.py anh_test.png"
    )

# =========================
# KHỞI TẠO AI TRƯỚC ĐỂ PHÂN LOẠI GIẤY TỜ
# =========================
print(f"📷 Ảnh đầu vào: {image_path}")
print(f"💾 Ảnh đầu ra: {output_path}")
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
suggested_finger = False
suggested_qr = False
suggested_id_num = False
suggested_name = False
suggested_dob = False
suggested_address = False
suggested_gender = False
suggested_nationality = False
suggested_identify_feature = False
document_type = "Không xác định (Tự chọn)"
suggested_cv_contact = False

# 1. Nếu là Căn cước công dân
# if 'can cuoc' in all_ocr_text or 'citizen' in all_ocr_text:
#     document_type = "Căn cước công dân (Mặt trước/sau)"
#     suggested_face = True
#     suggested_barcode = True
#     suggested_finger = True
#     suggested_qr = True
#     suggested_id_num = True
#     suggested_name = True
#     suggested_dob = True
#     suggested_address = True
# CCCD mặt sau
if (
    'dac diem nhan dang' in all_ocr_text or 'ngon tro trai' in all_ocr_text or 'ngon tro phai' in all_ocr_text or 'left index' in all_ocr_text or 'right index' in all_ocr_text or 'ngay cap' in all_ocr_text or 'date of issue' in all_ocr_text
):
    document_type = "Căn cước công dân - Mặt sau"
    document_side = "back"

    suggested_barcode = False
    suggested_finger = True

    suggested_address = False
    suggested_identity_feature = False

# CCCD mặt trước
elif (
    'can cuoc' in all_ocr_text or 'citizen identity card' in all_ocr_text or 'citizen' in all_ocr_text or 'quoc tich' in all_ocr_text or 'nationality' in all_ocr_text or 'ngay sinh' in all_ocr_text or 'date of birth' in all_ocr_text
):
    document_type = "Căn cước công dân - Mặt trước"
    document_side = "front"

    suggested_face = True
    suggested_barcode = False
    suggested_qr = True
    suggested_gender = False
    suggested_nationality = False

    suggested_id_num = True
    suggested_name = True
    suggested_dob = True
    suggested_address = True
# 2. Nếu là Bảo hiểm y tế
elif 'bao hiem y te' in all_ocr_text or 'bhyt' in all_ocr_text or 'the bhyt' in all_ocr_text:
    document_type = "Thẻ Bảo hiểm y tế"
    suggested_id_num = True  # Mã số BHYT
    suggested_name = False    # Họ tên
    suggested_dob = True     # Ngày sinh
    suggested_barcode = False # Thường BHYT có mã vạch ở đáy
    suggested_address = True
    # BHYT giấy không có QR, vân tay, khuôn mặt nên giữ False

# 3. Nếu là Thẻ sinh viên
elif 'sinh vien' in all_ocr_text or 'student' in all_ocr_text:
    document_type = "Thẻ sinh viên / Thẻ học sinh"
    suggested_id_num = True  # Mã số sinh viên
    suggested_name = True    # Họ tên
    suggested_dob = True     # Sinh ngày / Ngày sinh
    suggested_barcode = True # Mã vạch thẻ thư viện
    suggested_face = True    # Ảnh chân dung sinh viên
elif (
    'ho so' in all_ocr_text
    or 'cv' in all_ocr_text
    or 'resume' in all_ocr_text
    or 'lien he' in all_ocr_text
    or 'email' in all_ocr_text
    or 'dien thoai' in all_ocr_text
    or 'hoc van' in all_ocr_text
    or 'kinh nghiem' in all_ocr_text
    or 'ky nang' in all_ocr_text
):
    document_type = "CV / Hồ sơ cá nhân"

    # CV chỉ che ảnh chân dung + email/số điện thoại
    suggested_face = True
    suggested_cv_contact = True
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
    var_finger = tk.BooleanVar(value=suggested_finger)
    var_qr = tk.BooleanVar(value=suggested_qr)
    var_identity_feature = tk.BooleanVar(value=suggested_identify_feature)

    var_id_num = tk.BooleanVar(value=suggested_id_num)    
    var_name = tk.BooleanVar(value=suggested_name)      
    var_dob = tk.BooleanVar(value=suggested_dob)       
    var_address = tk.BooleanVar(value=suggested_address)  
    var_gender = tk.BooleanVar(value=suggested_gender)
    var_nationality = tk.BooleanVar(value=suggested_nationality) 
    var_cv_contact = tk.BooleanVar(value=suggested_cv_contact)

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
    tk.Checkbutton(f2, text="Che Đặc điểm nhận dạng", variable=var_identity_feature, bg="#F0F7F4", font=("Arial", 10)).pack(anchor="w", padx=20)
    tk.Checkbutton(f2, text="Che Họ và tên", variable=var_name, bg="#F0F7F4", font=("Arial", 10)).pack(anchor="w", padx=20)
    tk.Checkbutton(f2, text="Che Ngày tháng năm", variable=var_dob, bg="#F0F7F4", font=("Arial", 10)).pack(anchor="w", padx=20)
    tk.Checkbutton(f2, text="Che Giới tính", variable=var_gender, bg="#F0F7F4", font=("Arial", 10)).pack(anchor="w", padx=20)
    tk.Checkbutton(f2, text="Che Quốc tịch", variable=var_nationality, bg="#F0F7F4", font=("Arial", 10)).pack(anchor="w", padx=20)
    tk.Checkbutton(f2, text="Che Địa chỉ (Quê quán, Thường trú)", variable=var_address, bg="#F0F7F4", font=("Arial", 10)).pack(anchor="w", padx=20)
    tk.Checkbutton(f2,text="Che Email / Số điện thoại trong CV",variable=var_cv_contact,bg="#F0F7F4",font=("Arial", 10)).pack(anchor="w", padx=20)
    prefs = {}

    def on_submit():
        prefs['face'] = var_face.get()
        prefs['barcode'] = var_barcode.get()
        prefs['finger'] = var_finger.get()
        prefs['qr'] = var_qr.get()
        prefs['cv_contact'] = var_cv_contact.get()
        prefs['id_num'] = var_id_num.get()
        prefs['name'] = var_name.get()
        prefs['dob'] = var_dob.get()
        prefs['gender'] = var_gender.get()
        prefs['nationality'] = var_nationality.get()
        prefs['identity_feature'] = var_identity_feature.get()
        prefs['address'] = var_address.get()
        prefs['cv_contact'] = var_cv_contact.get()
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
REDACT_CV_CONTACT = user_choices.get('cv_contact', False)
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
    sensitive_keywords.extend(['ngay sinh', 'sinh ngay', 'date of birth', 'dob', 'ngay cap', 'date of issue', 'ngay het han','ngay bat dau hieu luc', 'ngay het hieu luc', 'co gia tri den', 'expiry', 'valid until', 'nam sinh:'])
    next_line_keywords.extend(['sinh ngay', 'ngay sinh', 'date of birth', 'ngay cap', 'ngay het han', 'expiry', 'co gia tri den', 'ngay bat dau hieu luc'])

if user_choices.get('gender'):
    sensitive_keywords.extend(['gioi tinh', 'sex', 'gender'])

if user_choices.get('nationality'):
    sensitive_keywords.extend(['quoc tich','nationality'])

if user_choices['address']:
    sensitive_keywords.extend(['que quan', 'place of origin', 'noi sinh', 'place of birth', 'noi thuong tru', 'thuong tru', 'place of residence', 'residence', 'dia chi', 'address', 'noi o hien tai', 'noi dki kcb ban dau', 'noi dk kcb', 'noi kcbbđ'])
    multi_line_keywords.extend(['que quan', 'place of origin', 'noi sinh', 'place of birth', 'noi thuong tru', 'thuong tru', 'place of residence', 'residence', 'dia chi', 'address', 'noi o hien tai'])
    vietnam_address_words.extend(['tp hcm', 'tphcm', 'ho chi minh', 'ha noi', 'da nang', 'can tho', 'hai phong', 'binh duong', 'dong nai', 'long an', 'ba ria', 'vung tau', 'quan', 'huyen', 'thi xa', 'thanh pho', 'phuong', 'xa', 'thi tran', 'ap', 'thon', 'khu pho', 'duong', 'so nha'])

if user_choices.get('cv_contact'):
    # CV contact xử lý riêng ở hàm redact_cv_contact_smart().
    # KHÔNG thêm email/e-mail/mail/contact vào sensitive_keywords/next_line_keywords,
    # vì logic che theo dòng tổng quát có thể kéo thanh đen qua cột phải.
    # Giữ nguyên từ khóa điện thoại để không ảnh hưởng logic che SĐT hiện tại.
    sensitive_keywords.extend([
        'dien thoai', 'so dien thoai', 'phone', 'mobile', 'tel'
    ])

    next_line_keywords.extend([
        'dien thoai', 'so dien thoai', 'phone', 'mobile', 'tel'
    ])
# sensitive_keywords.extend(['dac diem nhan dang', 'personal identification', 'nhan dang'])
# multi_line_keywords.extend(['dac diem nhan dang', 'personal identification'])
if user_choices.get('identity_feature'):
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

def find_label_end_x(line, keywords):
    """
    Tìm vị trí kết thúc phần nhãn trên cùng 1 dòng OCR.
    Ví dụ: 'Sinh ngày 01/01/2000' -> trả về x2 của chữ 'ngày',
    để chỉ che phần dữ liệu nằm sau nhãn, không che luôn nhãn.
    """
    items = sorted(line['items'], key=lambda i: i['x1'])
    cleaned_tokens = []

    for item in items:
        token = normalize_text(item['text'])
        token = re.sub(r'[^a-z0-9 ]+', ' ', token)
        token = re.sub(r'\s+', ' ', token).strip()
        cleaned_tokens.append(token)

    sorted_keywords = sorted(keywords, key=lambda k: len(k.split()), reverse=True)

    for kw in sorted_keywords:
        kw_clean = normalize_text(kw)
        kw_clean = re.sub(r'[^a-z0-9 ]+', ' ', kw_clean)
        kw_clean = re.sub(r'\s+', ' ', kw_clean).strip()
        kw_parts = kw_clean.split()

        if not kw_parts:
            continue

        for i in range(len(cleaned_tokens) - len(kw_parts) + 1):
            chunk = " ".join(cleaned_tokens[i:i + len(kw_parts)])
            if chunk == kw_clean:
                return items[i + len(kw_parts) - 1]['x2']

    return None

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
def redact_barcode_area(img):
    """
    Làm mờ mã vạch ở khu vực phía dưới ảnh.
    Phù hợp với thẻ sinh viên như ảnh SGU.
    """
    img_h, img_w = img.shape[:2]

    x1 = int(img_w * 0.35)
    y1 = int(img_h * 0.83)
    x2 = int(img_w * 0.92)
    y2 = int(img_h * 0.98)

    pixelate_region(img, x1, y1, x2, y2, blocks=10)
def redact_cv_portrait_area(img):
    """
    Che ảnh chân dung trong CV.
    Với mẫu CV bạn gửi, ảnh nằm ở góc trái phía trên.
    """
    img_h, img_w = img.shape[:2]

    x1 = int(img_w * 0.07)
    y1 = int(img_h * 0.10)
    x2 = int(img_w * 0.36)
    y2 = int(img_h * 0.33)

    pixelate_region(img, x1, y1, x2, y2, blocks=12)
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


    # Nếu người dùng chọn che số định danh
    if user_choices['id_num']:
        norm_text = normalize_text(text)

        id_labels = [
            'ma so',
            'ma the',
            'so the',
            'so bhyt',
            'so cccd',
            'so dinh danh',
            'id no', 'ma so bhyt'
        ]

        has_id_label = any(k in norm_text for k in id_labels)

        # Với BHYT: chỉ bắt mã số khi dòng có nhãn mã số/số thẻ.
        if document_type.startswith("Thẻ Bảo hiểm"):
            if has_id_label and re.search(r'(?:\d[\s.-]?){10,15}', text):
                return True
            return False

        # Với CCCD/thẻ khác: giữ logic bắt số định danh.
        if re.search(r'(?:\d[\s.-]?){12}', text) or re.search(r'(?:\d[\s.-]?){9}', text):
            return True

        if has_id_label and re.search(r'\d{10,15}', compact_text):
            return True

    # Nếu người dùng chọn che ngày tháng năm sinh
    # if user_choices['dob']:
    #     if re.search(r'\d{2}[\/\-.]\d{2}[\/\-.]\d{4}', text) or re.search(r'\d{4}[\/\-.]\d{2}[\/\-.]\d{2}', text):
    #         return True
    if user_choices['dob']:
        norm_text = normalize_text(text)
        dob_labels = ['ngay sinh', 'sinh ngay', 'date of birth', 'dob'
        ]

        has_dob_label = any(label in norm_text for label in dob_labels)

        if has_dob_label:
            if (
                re.search(r'\d{2}[\/\-.]\d{2}[\/\-.]\d{4}', text) or re.search(r'\d{4}[\/\-.]\d{2}[\/\-.]\d{2}', text)
            ):
                return True
    return False
def redact_cv_contact_smart(img, ocr_items, line_items):
    """
    Che email và số điện thoại trong CV theo đúng vùng thông tin liên hệ.

    Nguyên tắc:
    - Không dùng keyword EMAIL để che nguyên dòng OCR nữa, vì dễ kéo qua cột phải.
    - Nếu OCR đọc được email: chỉ che các OCR item thuộc email.
    - Nếu OCR không đọc được email: tìm dòng nhãn EMAIL rồi dùng xử lý ảnh trong khoảng
      từ EMAIL đến mục kế tiếp, che đúng các cụm chữ/underline thật sự xuất hiện.
    - Không ảnh hưởng logic CCCD / thẻ sinh viên / barcode / mặt.
    """
    img_h, img_w = img.shape[:2]
    left_col_limit = int(img_w * 0.45)

    email_pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z0-9]{2,}(?:\.[a-zA-Z0-9]{2,})*'

    phone_pattern = r'''
    (?<!\d)
    (?:
        (?:\+?84|0)[\s.-]?(?:\d[\s.-]?){8,10}
        |
        \d{3}[\s.-]?\d{3}[\s.-]?\d{4}
    )
    (?!\d)
    '''

    def is_left_cv_item(item):
        return item['x1'] < left_col_limit

    def merge_boxes_local(boxes, distance_x=8, distance_y=8):
        if not boxes:
            return []
        boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
        merged = []
        for box in boxes:
            x1, y1, x2, y2 = box
            added = False
            for idx, (mx1, my1, mx2, my2) in enumerate(merged):
                overlap_y = y1 <= my2 + distance_y and y2 >= my1 - distance_y
                overlap_x = x1 <= mx2 + distance_x and x2 >= mx1 - distance_x
                if overlap_y and overlap_x:
                    merged[idx] = (min(mx1, x1), min(my1, y1), max(mx2, x2), max(my2, y2))
                    added = True
                    break
            if not added:
                merged.append(box)
        return merged


    def redact_email_rect(x1, y1, x2, y2):
        """Che email riêng: nới lên phía trên một chút để không lòi mép chữ."""
        img_h, img_w = img.shape[:2]
        top_extra = 7      # tăng số này nếu vẫn còn lòi phía trên
        bottom_extra = 4
        left_extra = 3
        right_extra = 3
        redact_rect(
            img,
            max(0, x1 - left_extra),
            max(0, y1 - top_extra),
            min(img_w, x2 + right_extra),
            min(img_h, y2 + bottom_extra),
            padding=0
        )

    def redact_email_match_in_items(items):
        """Ghép các item trên cùng một dòng rồi chỉ che item thuộc phần email."""
        items = [i for i in sorted(items, key=lambda k: k['x1']) if is_left_cv_item(i)]
        if not items:
            return False

        compact_text = ""
        parts = []
        for item in items:
            word = item['text'].strip()
            if not word:
                continue
            word_compact = re.sub(r'\s+', '', word)
            start = len(compact_text)
            compact_text += word_compact
            end = len(compact_text)
            parts.append({'item': item, 'start': start, 'end': end})

        found = False
        for match in re.finditer(email_pattern, compact_text):
            m_start, m_end = match.span()
            matched_items = [p['item'] for p in parts if p['end'] > m_start and p['start'] < m_end]
            if not matched_items:
                continue
            x1 = min(i['x1'] for i in matched_items)
            y1 = min(i['y1'] for i in matched_items)
            x2 = max(i['x2'] for i in matched_items)
            y2 = max(i['y2'] for i in matched_items)
            redact_email_rect(x1, y1, x2, y2)
            found = True
        return found

    def redact_phone_match_in_items(items):
        """Giữ cách che số điện thoại theo OCR item, chỉ trong cột trái CV."""
        items = [i for i in sorted(items, key=lambda k: k['x1']) if is_left_cv_item(i)]
        if not items:
            return False

        compact_text = ""
        parts = []
        for item in items:
            word = item['text'].strip()
            if not word:
                continue
            word_compact = re.sub(r'\s+', '', word)
            start = len(compact_text)
            compact_text += word_compact
            end = len(compact_text)
            parts.append({'item': item, 'start': start, 'end': end})

        found = False
        for match in re.finditer(phone_pattern, compact_text, re.VERBOSE):
            m_start, m_end = match.span()
            matched_items = [p['item'] for p in parts if p['end'] > m_start and p['start'] < m_end]
            if not matched_items:
                continue
            x1 = min(i['x1'] for i in matched_items)
            y1 = min(i['y1'] for i in matched_items)
            x2 = max(i['x2'] for i in matched_items)
            y2 = max(i['y2'] for i in matched_items)
            redact_rect(img, x1, y1, x2, y2, padding=3)
            found = True
        return found

    # 1) Nếu OCR bắt được email / phone trong từng item riêng lẻ thì che item đó trước.
    for item in ocr_items:
        if not is_left_cv_item(item):
            continue
        text = item['text'].strip()
        if not text:
            continue
        if re.search(email_pattern, re.sub(r'\s+', '', text)):
            redact_email_rect(item['x1'], item['y1'], item['x2'], item['y2'])
        if re.search(phone_pattern, text, re.VERBOSE):
            redact_rect(img, item['x1'], item['y1'], item['x2'], item['y2'], padding=3)

    # 2) Email / phone bị OCR tách nhiều mảnh nhưng vẫn cùng dòng.
    email_found_by_ocr = False
    for line in line_items:
        email_found_by_ocr = redact_email_match_in_items(line['items']) or email_found_by_ocr
        redact_phone_match_in_items(line['items'])

    # 3) Email bị OCR không nhận ra: không che đại 1 vùng cố định.
    #    Thay vào đó, tìm nhãn EMAIL rồi dò các cụm chữ/underline thật trong vùng giữa EMAIL và mục kế tiếp.
    email_label_lines = []
    for line in line_items:
        norm = line['norm_text']
        if re.search(r'\b(e\s*-?\s*mail|email|mail)\b', norm) and line['x1'] < left_col_limit:
            email_label_lines.append(line)

    next_section_keywords = [
        'so thich', 'hobbies', 'ky nang', 'skills', 'hoc van', 'education',
        'kinh nghiem', 'experience', 'du an', 'projects'
    ]

    for email_line in email_label_lines:
        y_start = email_line['y2'] + 1
        y_end = min(img_h, y_start + int(img_h * 0.16))

        # Nếu có heading kế tiếp như SỞ THÍCH thì dừng trước heading đó.
        for line in line_items:
            if line['y1'] <= email_line['y2']:
                continue
            if line['x1'] >= left_col_limit:
                continue
            if any(k in line['norm_text'] for k in next_section_keywords):
                y_end = min(y_end, max(y_start + 1, line['y1'] - 3))
                break

        # Ưu tiên OCR item nằm dưới EMAIL trong vùng này: nếu item có @ thì che đúng item.
        items_below = [
            item for item in ocr_items
            if is_left_cv_item(item)
            and item['y1'] >= y_start
            and item['y2'] <= y_end
        ]
        if redact_email_match_in_items(items_below):
            continue

        # Fallback bằng xử lý ảnh: tìm các cụm pixel chữ/underline trong ROI, không che cả dòng/cả khối.
        x_start = max(0, email_line['x1'] - 2)
        x_end = left_col_limit
        if y_end <= y_start or x_end <= x_start:
            continue

        roi = img[y_start:y_end, x_start:x_end]
        if roi.size == 0:
            continue

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # Text/link thường tối hơn nền hoặc có màu bão hòa hơn nền xám nhạt.
        dark_mask = gray < 185
        saturated_mask = hsv[:, :, 1] > 35
        mask = (dark_mask | saturated_mask).astype(np.uint8) * 255

        # Dọn nhiễu và nối các nét chữ gần nhau.
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 2))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        kernel_join = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3))
        mask = cv2.dilate(mask, kernel_join, iterations=1)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w < 12 or h < 3:
                continue
            if h > (y_end - y_start) * 0.8:
                continue
            boxes.append((x_start + x, y_start + y, x_start + x + w, y_start + y + h))

        for x1, y1, x2, y2 in merge_boxes_local(boxes, distance_x=10, distance_y=6):
            # Che từng cụm thật sự thấy được, hỗ trợ email xuống nhiều dòng.
            redact_email_rect(x1, y1, x2, y2)

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
# =========================
# LOGIC CHE TEXT THEO LABEL - FIX THẺ SINH VIÊN
# =========================
# OCR của thẻ sinh viên có thể đọc thành:
#   "và tên:"      rồi dòng sau mới là tên
#   "Sinh ngày:"   rồi dòng sau mới là ngày sinh
# Nếu dùng logic keyword cũ, code dễ che luôn nhãn hoặc che nhầm dòng kế tiếp.
# Khối này tách riêng label và value:
# - Label đứng riêng: KHÔNG che label, chỉ che dòng value kế tiếp.
# - Label + value cùng dòng: chỉ che phần value sau dấu ":" hoặc sau cụm label.

def clean_label_text(text):
    text = normalize_text(text)
    text = re.sub(r'[^a-z0-9 ]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_any_label_line(line, label_keywords):
    norm = clean_label_text(line['text'])
    return any(re.search(r'\b' + re.escape(clean_label_text(kw)) + r'\b', norm) for kw in label_keywords)

def line_value_after_colon(line):
    # Trả về True nếu sau dấu ':' còn ký tự thật sự, ví dụ "Sinh ngày: 14-05-2006".
    text = line['text']
    if ':' not in text:
        return False
    after = text.split(':', 1)[1]
    after = re.sub(r'[^0-9A-Za-zÀ-ỹ]+', '', after)
    return bool(after)

def line_is_label_only(line, label_keywords):
    # Ví dụ: "Sinh ngày:" hoặc OCR thành "Sinh ngày" -> chỉ là label, chưa có dữ liệu.
    norm = clean_label_text(line['text'])
    labels = [clean_label_text(k) for k in label_keywords]

    if norm in labels:
        return True

    # Cho phép trường hợp OCR có dấu ':' / ký tự thừa nhưng sau ':' không có value.
    if ':' in line['text'] and not line_value_after_colon(line):
        return any(re.search(r'\b' + re.escape(k) + r'\b', norm) for k in labels)

    return False

def next_line_is_another_label(line):
    all_label_keywords = [
        'ho va ten', 'ho ten', 'va ten', 'ten', 'full name', 'name',
        'sinh ngay', 'ngay sinh', 'date of birth', 'dob', 'nam sinh',
        'ma so', 'ma the', 'mssv', 'student id', 'so the'
    ]
    return is_any_label_line(line, all_label_keywords)

def add_next_value_line(index, scan_next=3):
    # Tìm dòng dữ liệu kế tiếp, bỏ qua dòng rỗng/heading khác nếu có.
    for j in range(index + 1, min(index + 1 + scan_next, len(line_items))):
        candidate = line_items[j]
        if next_line_is_another_label(candidate):
            break
        if candidate['x2'] - candidate['x1'] < 5 or candidate['y2'] - candidate['y1'] < 5:
            continue
        redact_boxes.append((candidate['x1'], candidate['y1'], candidate['x2'], candidate['y2']))
        break

# def add_value_on_same_line(line, label_keywords):
#     colon_x = None
#     for it in sorted(line['items'], key=lambda i: i['x1']):
#         if ':' in it['text']:
#             colon_x = it['x2']
#             break

#     label_end_x = find_label_end_x(line, label_keywords)

#     start_x = colon_x or label_end_x
#     if start_x and line['x2'] > start_x + 5:
#         redact_boxes.append((start_x, line['y1'], line['x2'], line['y2']))
#         return True
#     return False
def find_next_label_start_x(line, current_start_x, all_label_keywords):
    items = sorted(line['items'], key=lambda i: i['x1'])

    for item in items:
        if item['x1'] <= current_start_x + 3:
            continue

        item_norm = clean_label_text(item['text'])

        for kw in all_label_keywords:
            kw_norm = clean_label_text(kw)
            if item_norm == kw_norm or kw_norm in item_norm:
                return item['x1']

    return None


def add_value_on_same_line(line, label_keywords):
    items = sorted(line['items'], key=lambda i: i['x1'])

    label_end_x = find_label_end_x(line, label_keywords)
    if not label_end_x:
        return False

    colon_x = None

    # Chỉ lấy dấu ':' nằm sau đúng label đang xử lý
    for it in items:
        if it['x1'] < label_end_x - 3:
            continue

        if ':' in it['text']:
            colon_x = it['x2']
            break

    start_x = colon_x or label_end_x

    all_field_labels = (
        name_label_keywords
        + dob_label_keywords
        + gender_label_keywords
        + nationality_label_keywords
        + [
            'que quan',
            'place of origin',
            'noi thuong tru',
            'thuong tru',
            'place of residence',
            'residence',
            'dia chi',
            'address'
        ]
    )

    next_label_x = find_next_label_start_x(line, start_x, all_field_labels)
    end_x = next_label_x - 5 if next_label_x else line['x2']

    if end_x > start_x + 5:
        redact_boxes.append((start_x, line['y1'], end_x, line['y2']))
        return True

    return False
def find_label_start_x(line, keywords):
    items = sorted(line['items'], key=lambda i: i['x1'])
    cleaned_tokens = []

    for item in items:
        token = normalize_text(item['text'])
        token = re.sub(r'[^a-z0-9 ]+', ' ', token)
        token = re.sub(r'\s+', ' ', token).strip()
        cleaned_tokens.append(token)

    sorted_keywords = sorted(keywords, key=lambda k: len(k.split()), reverse=True)

    for kw in sorted_keywords:
        kw_clean = normalize_text(kw)
        kw_clean = re.sub(r'[^a-z0-9 ]+', ' ', kw_clean)
        kw_clean = re.sub(r'\s+', ' ', kw_clean).strip()
        kw_parts = kw_clean.split()

        for i in range(len(cleaned_tokens) - len(kw_parts) + 1):
            chunk = " ".join(cleaned_tokens[i:i + len(kw_parts)])
            if chunk == kw_clean:
                return items[i]['x1']

    return None

redact_boxes = []
name_label_keywords = ['ho va ten', 'ho ten', 'va ten', 'ten', 'full name', 'name']
dob_label_keywords = ['sinh ngay', 'ngay sinh', 'date of birth', 'dob', 'nam sinh']
gender_label_keywords = ['gioi tinh', 'sex', 'gender']
nationality_label_keywords = ['quoc tich', 'nationality']

for index, line in enumerate(line_items):
    is_sensitive = False
    norm = line['norm_text']
    text = line['text']

    address_labels = [
    'que quan',
    'place of origin',
    'noi thuong tru',
    'thuong tru',
    'place of residence',
    'residence',
    'dia chi',
    'address'
]

    if not user_choices.get('address') and any(k in norm for k in address_labels):
        continue
    # Fix riêng cho thẻ sinh viên: "Sinh ngày:" là label, không phải value.
    # Vì user đang tick Che Họ tên / Che Ngày sinh, ta xử lý label trước generic keyword.
    handled_label = False

    if user_choices.get('name') and is_any_label_line(line, name_label_keywords):
        colon_x = None

        for it in sorted(line['items'], key=lambda i: i['x1']):
            if ':' in it['text']:
                colon_x = it['x2']
                break
        if colon_x and line['x2'] > colon_x + 5:
            redact_boxes.append((colon_x + 3, line['y1'], line['x2'] + 5, line['y2']))
        elif line_is_label_only(line, name_label_keywords):
            add_next_value_line(index, scan_next=3)
        else:
            add_value_on_same_line(line, name_label_keywords)
        handled_label = True

    bhyt_id_keywords = ['ma so', 'ma the', 'so the', 'so bhyt']

    if user_choices.get('id_num') and document_type.startswith("Thẻ Bảo hiểm") and has_keyword(norm, bhyt_id_keywords):
        label_end_x = find_label_end_x(line, bhyt_id_keywords)

        if label_end_x and line['x2'] > label_end_x + 8:
            redact_boxes.append((label_end_x + 3, line['y1'], line['x2'] + 5, line['y2']))
        elif index + 1 < len(line_items):
            next_line = line_items[index + 1]
            redact_boxes.append((next_line['x1'], next_line['y1'], next_line['x2'] + 5, next_line['y2']))

        handled_label = True

    kcbbd_keywords = [
    'noi dki kcb ban dau',
    'noi dk kcb ban dau',
    'noi dk kcb',
    'noi kcbbd',
    'noi kcbbđ',
    'kcbbd',
    'kcb ban dau',
    'noi dang ky kham chua benh ban dau'
    ]

    if user_choices.get('address') and has_keyword(norm, kcbbd_keywords):
        label_end_x = find_label_end_x(line, kcbbd_keywords)

        # Dữ liệu nằm cùng dòng sau tiêu đề
        if label_end_x and line['x2'] > label_end_x + 8:
            redact_boxes.append((
                label_end_x + 3,
                line['y1'],
                line['x2'] + 5,
                line['y2']
            ))

        # Dữ liệu nằm dòng dưới
        else:
            for j in range(index + 1, min(index + 3, len(line_items))):
                redact_boxes.append((
                    line_items[j]['x1'],
                    line_items[j]['y1'],
                    line_items[j]['x2'] + 5,
                    line_items[j]['y2']
                ))
                

        handled_label = True

    if user_choices.get('dob') and (
        'ngay sinh' in norm
        or 'sinh ngay' in norm
        or 'date of birth' in norm
        or 'dob' in norm or 'ngay bat dau hieu luc' in norm or 'ngay het hieu luc' in norm
    ):
        m = re.search(r'\d{2}[\/\-.]\d{2}[\/\-.]\d{4}', text)

        if m:
            x1 = int(line['x1'] + (line['x2'] - line['x1']) * (m.start() / len(text)))
            x2 = int(line['x1'] + (line['x2'] - line['x1']) * (m.end() / len(text)))
            redact_boxes.append((max(0, x1 - 90), line['y1'], x2 + 5, line['y2']))
        else:
            add_next_value_line(index, scan_next=2)

        handled_label = True
        
    # Xử lý riêng dòng: Giới tính ... Quốc tịch ...
    if 'gioi tinh' in norm and 'quoc tich' in norm:
        gt_x = int(line['x1'] + (line['x2'] - line['x1']) * 0.28)
        qt_x = int(line['x1'] + (line['x2'] - line['x1']) * 0.52)

        if user_choices.get('gender'):
            redact_boxes.append((gt_x, line['y1'], qt_x - 5, line['y2']))

        if user_choices.get('nationality'):
            redact_boxes.append((qt_x, line['y1'], line['x2'], line['y2']))

        handled_label = True
    
    if handled_label:
        continue
    
    if is_safe_phrase(norm) and not line_has_sensitive_pattern(text): continue
    if line_has_sensitive_pattern(text): is_sensitive = True
    if has_keyword(norm, sensitive_keywords): is_sensitive = True
    if has_keyword(norm, vietnam_address_words) and len(norm) >= 8: is_sensitive = True

    if has_keyword(norm, multi_line_keywords):
        for j in range(index + 1, min(index + 5, len(line_items))):
            redact_boxes.append((line_items[j]['x1'] - 90, line_items[j]['y1'], line_items[j]['x2'] + 5, line_items[j]['y2']))

    if has_keyword(norm, next_line_keywords):
        for j in range(index + 1, min(index + 2, len(line_items))):  # bắt đầu từ dòng SAU
            next_norm = line_items[j]['norm_text']

            if not user_choices.get('address') and any(k in next_norm for k in address_labels):
                continue
            if not next_line_is_another_label(line_items[j]):
                redact_boxes.append((line_items[j]['x1'] - 90, line_items[j]['y1'], line_items[j]['x2'] + 5, line_items[j]['y2']))

    if is_sensitive:
        colon_x = None
        for it in sorted(line['items'], key=lambda i: i['x1']):
            if ':' in it['text']:
                colon_x = it['x2']
                break

        # Với mọi giấy tờ, nếu có label "Sinh ngày" / "Họ và tên" trên cùng dòng,
        # chỉ che phần dữ liệu sau label, không che luôn chữ label.
        label_end_x = find_label_end_x(line, name_label_keywords + dob_label_keywords + gender_label_keywords + nationality_label_keywords)

        if colon_x and line['x2'] > colon_x + 5:
            redact_boxes.append((colon_x, line['y1'], line['x2'], line['y2']))
        elif label_end_x and line['x2'] > label_end_x + 5:
            redact_boxes.append((label_end_x, line['y1'], line['x2'], line['y2']))
        elif not is_any_label_line(line, name_label_keywords + dob_label_keywords + gender_label_keywords + nationality_label_keywords):
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
        box_data = {'x1': max(0, x1 - int(h_text * 3.0)), 'y1': max(0, y1 - int(h_text * 14)), 'x2': min(img.shape[1], x2 + int(h_text * 3.0)), 'y2': max(0, y1 + int (h_text  * 0.3)), 'text': item['text']}
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
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )

    gray_face = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    for (x, y, w, h) in face_cascade.detectMultiScale(
        gray_face,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(40, 40)
    ):
        pixelate_region(img, x, y, x + w, y + h, blocks=8)

    # Nếu là CV thì dùng vùng ảnh CV riêng
    if document_type.startswith("CV"):
        redact_cv_portrait_area(img)

    # Nếu không phải CV thì giữ logic cũ cho CCCD / thẻ sinh viên
    else:
        f_x1 = int(img_w * FACE_AREA_RATIO["x1"])
        f_y1 = int(img_h * FACE_AREA_RATIO["y1"])
        f_x2 = int(img_w * FACE_AREA_RATIO["x2"])
        f_y2 = int(img_h * FACE_AREA_RATIO["y2"])

        pixelate_region(img, f_x1, f_y1, f_x2, f_y2, blocks=10)
if REDACT_CV_CONTACT:
    redact_cv_contact_smart(img, ocr_items, line_items)
if REDACT_BARCODE:
    redact_barcode_area(img)
cv2.imwrite(output_path, img)
print(f"\n✨ Xử lý hoàn tất! Đã lưu ảnh tại: {output_path}")