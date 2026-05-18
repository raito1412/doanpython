import cv2
import easyocr
import re
import unicodedata

# =========================
# CẤU HÌNH
# =========================

image_path = 'anh_test.jpg'
output_path = 'redacted_output.jpg'

reader = easyocr.Reader(['vi', 'en'], gpu=False)

# Nếu muốn che mặt / ảnh chân dung theo vùng cố định, bật True
REDACT_FACE_AREA = False

# Nếu giấy tờ là CCCD mặt trước, có thể bật để che vùng ảnh chân dung bên trái
FACE_AREA_RATIO = {
    "x1": 0.03,
    "y1": 0.28,
    "x2": 0.30,
    "y2": 0.82,
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

def get_rect_from_bbox(bbox):
    xs = [point[0] for point in bbox]
    ys = [point[1] for point in bbox]

    x1 = int(min(xs))
    y1 = int(min(ys))
    x2 = int(max(xs))
    y2 = int(max(ys))

    return x1, y1, x2, y2

def redact_rect(img, x1, y1, x2, y2, padding=8):
    img_h, img_w = img.shape[:2]

    x1 = max(0, int(x1) - padding)
    y1 = max(0, int(y1) - padding)
    x2 = min(img_w, int(x2) + padding)
    y2 = min(img_h, int(y2) + padding)

    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), -1)

def pixelate_region(img, x1, y1, x2, y2, blocks=12):

    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(img.shape[1], x2)
    y2 = min(img.shape[0], y2)

    roi = img[y1:y2, x1:x2]

    if roi.size == 0:
        return

    h, w = roi.shape[:2]

    # thu nhỏ mạnh
    temp = cv2.resize(
        roi,
        (blocks, blocks),
        interpolation=cv2.INTER_LINEAR
    )

    # phóng to lại để tạo pixel effect
    pixelated = cv2.resize(
        temp,
        (w, h),
        interpolation=cv2.INTER_NEAREST
    )

    img[y1:y2, x1:x2] = pixelated

def detect_and_redact_codes(img):

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ====================================
    # QR CODE
    # ====================================

    qr_detector = cv2.QRCodeDetector()

    scale = 3

    big = cv2.resize(
        gray,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC
    )

    retval, points = qr_detector.detectMulti(big)

    if retval:

        for qr_points in points:

            qr_points = qr_points / scale

            xs = [p[0] for p in qr_points]
            ys = [p[1] for p in qr_points]

            x1 = int(min(xs))
            y1 = int(min(ys))
            x2 = int(max(xs))
            y2 = int(max(ys))

            pixelate_region(
                img,
                x1,
                y1,
                x2,
                y2,
                blocks=8
            )

def redact_ratio_area(img, area, padding=0):
    img_h, img_w = img.shape[:2]

    x1 = int(img_w * area["x1"])
    y1 = int(img_h * area["y1"])
    x2 = int(img_w * area["x2"])
    y2 = int(img_h * area["y2"])

    redact_rect(img, x1, y1, x2, y2, padding=padding)

def merge_boxes(boxes):
    if not boxes:
        return None

    x1 = min(box[0] for box in boxes)
    y1 = min(box[1] for box in boxes)
    x2 = max(box[2] for box in boxes)
    y2 = max(box[3] for box in boxes)

    return x1, y1, x2, y2

def line_has_sensitive_pattern(text):
    compact_text = re.sub(r'\s+', '', text)
    digits_only = re.sub(r'\D', '', text)

    patterns = [
        r'(?:\d[\s.-]?){12}',                              # CCCD 12 số
        r'(?:\d[\s.-]?){9}',                               # CMND 9 số
        r'\d{2}[\/\-.]\d{2}[\/\-.]\d{4}',                  # ngày 14/05/2006
        r'\d{4}[\/\-.]\d{2}[\/\-.]\d{2}',                  # ngày 2006-05-14
        r'0\d{9,10}',                                      # số điện thoại VN
        r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', # email
        r'\d{10,13}',                                      # mã số thuế / mã định danh khác
        r'[A-Z]\d{7,8}',                                   # hộ chiếu phổ biến: B1234567
        r'\d{2}[A-Z]-\d{3}\.\d{2}',                        # biển số xe 59A-123.45
        r'\d{2}[A-Z]\d-\d{3}\.\d{2}',                      # biển số xe 59A1-123.45
        r'\d{2}[A-Z][A-Z]-\d{3}\.\d{2}', 
    ]

    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True

    # Nếu một dòng có nhiều số thì thường là mã định danh, ngày tháng, số giấy tờ
    if len(digits_only) >= 8:
        return True

    # Dòng có dạng CCCD bị OCR tách/kèm ký tự lạ
    if len(digits_only) in [9, 10, 11, 12, 13]:
        return True

    return False

# =========================
# TỪ KHÓA NHẠY CẢM
# =========================

sensitive_keywords = [
    # Định danh cá nhân
    'so',
    'so the',
    'so cccd',
    'cccd',
    'cmnd',
    'cmt',
    'can cuoc',
    'can cuoc cong dan',
    'citizen identity',
    'citizen identity card',
    'identity card',
    'id card',
    'passport',
    'ho chieu',
    'so ho chieu',

    # Họ tên
    'ho va ten',
    'ho ten',
    'ten',
    'full name',
    'name',

    # Ngày tháng
    'ngay sinh',
    'sinh ngay',
    'date of birth',
    'dob',
    'ngay cap',
    'date of issue',
    'ngay het han',
    'co gia tri den',
    'expiry',
    'valid until',

    # Thông tin cá nhân
    'gioi tinh',
    'sex',
    'gender',
    'quoc tich',
    'nationality',
    'dan toc',
    'religion',
    'ton giao',

    # Địa chỉ
    'que quan',
    'place of origin',
    'noi sinh',
    'place of birth',
    'noi thuong tru',
    'thuong tru',
    'place of residence',
    'residence',
    'dia chi',
    'address',
    'noi o hien tai',

    # Giấy tờ / tài chính / y tế / khác
    'ma so thue',
    'tax code',
    'mst',
    'so bhxh',
    'bao hiem xa hoi',
    'so bhyt',
    'bao hiem y te',
    'bien so',
    'license plate',
    'so dien thoai',
    'dien thoai',
    'phone',
    'email',
]

# Những từ khóa này thường có dữ liệu nằm ở cùng dòng hoặc nhiều dòng bên dưới
multi_line_keywords = [
    'que quan',
    'place of origin',
    'noi sinh',
    'place of birth',
    'noi thuong tru',
    'thuong tru',
    'place of residence',
    'residence',
    'dia chi',
    'address',
    'noi o hien tai',
]

# Những từ khóa này thường có giá trị nằm ngay dòng sau hoặc cùng dòng
next_line_keywords = [
    'ho va ten',
    'ho ten',
    'full name',
    'name',
    'ngay sinh',
    'date of birth',
    'ngay cap',
    'date of issue',
    'ngay het han',
    'expiry',
    'co gia tri den',
    'quoc tich',
    'nationality',
    'gioi tinh',
    'sex',
    'gender',
]

# Các địa danh/từ thường xuất hiện trong địa chỉ Việt Nam
vietnam_address_words = [
    'tp hcm',
    'tphcm',
    'ho chi minh',
    'ha noi',
    'da nang',
    'can tho',
    'hai phong',
    'binh duong',
    'dong nai',
    'long an',
    'ba ria',
    'vung tau',
    'quan',
    'huyen',
    'thi xa',
    'thanh pho',
    'phuong',
    'xa',
    'thi tran',
    'ap',
    'thon',
    'khu pho',
    'duong',
    'so nha',
]

# =========================
# ĐỌC ẢNH
# =========================

img = cv2.imread(image_path)

# =========================
# PHÁT HIỆN KHUÔN MẶT
# =========================

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

faces = face_cascade.detectMultiScale(
    gray,
    scaleFactor=1.1,
    minNeighbors=5,
    minSize=(40, 40)
)

for (x, y, w, h) in faces:
     pixelate_region(
        img,
        x,
        y,
        x + w,
        y + h,
        blocks=8
    )
# =========================
# QR CODE 
# =========================

detect_and_redact_codes(img)

# =========================
# OCR
# =========================

results = reader.readtext(image_path)

print("===== NỘI DUNG OCR =====")

ocr_items = []

for bbox, text, conf in results:
    text = text.strip()

    if not text:
        continue

    x1, y1, x2, y2 = get_rect_from_bbox(bbox)

    item = {
        'text': text,
        'norm_text': normalize_text(text),
        'conf': conf,
        'x1': x1,
        'y1': y1,
        'x2': x2,
        'y2': y2,
        'center_y': (y1 + y2) // 2,
        'height': y2 - y1,
    }

    ocr_items.append(item)
    print(text)

ocr_items = sorted(ocr_items, key=lambda item: (item['y1'], item['x1']))

# =========================
# GOM OCR THEO DÒNG
# =========================

lines = []

for item in ocr_items:
    added = False

    for line in lines:
        # Ngưỡng gom dòng linh hoạt theo chiều cao chữ
        avg_height = max(12, item['height'])
        if abs(item['center_y'] - line['center_y']) < max(18, avg_height * 0.7):
            line['items'].append(item)

            centers = [i['center_y'] for i in line['items']]
            line['center_y'] = sum(centers) // len(centers)

            added = True
            break

    if not added:
        lines.append({
            'center_y': item['center_y'],
            'items': [item]
        })

line_items = []

for line in lines:
    items = sorted(line['items'], key=lambda item: item['x1'])

    line_text = ' '.join(item['text'] for item in items)
    norm_line_text = normalize_text(line_text)

    x1 = min(item['x1'] for item in items)
    y1 = min(item['y1'] for item in items)
    x2 = max(item['x2'] for item in items)
    y2 = max(item['y2'] for item in items)

    line_items.append({
        'text': line_text,
        'norm_text': norm_line_text,
        'x1': x1,
        'y1': y1,
        'x2': x2,
        'y2': y2,
        'center_y': (y1 + y2) // 2,
        'height': y2 - y1,
    })

line_items = sorted(line_items, key=lambda item: item['y1'])

print("\n===== NỘI DUNG OCR THEO DÒNG =====")

for line in line_items:
    print(line['text'])

# =========================
# XÁC ĐỊNH VÙNG CẦN CHE
# =========================

redact_boxes = []

for index, line in enumerate(line_items):
    is_sensitive = False

    norm = line['norm_text']
    text = line['text']

    # 1. Regex số giấy tờ, ngày sinh, điện thoại, email...
    if line_has_sensitive_pattern(text):
        is_sensitive = True

    # 2. Keyword nhạy cảm
    if any(keyword in norm for keyword in sensitive_keywords):
        is_sensitive = True

    # 3. Dòng giống địa chỉ Việt Nam
    if any(word in norm for word in vietnam_address_words) and len(norm) >= 8:
        is_sensitive = True

    # 4. Nếu phát hiện keyword nhiều dòng, che dòng đó + 4 dòng dưới
    if any(keyword in norm for keyword in multi_line_keywords):
        for j in range(index, min(index + 5, len(line_items))):
            redact_boxes.append((
                line_items[j]['x1'],
                line_items[j]['y1'],
                line_items[j]['x2'],
                line_items[j]['y2']
            ))

    # 5. Nếu phát hiện keyword có giá trị ngay sau, che dòng đó + 1 dòng dưới
    if any(keyword in norm for keyword in next_line_keywords):
        for j in range(index, min(index + 2, len(line_items))):
            redact_boxes.append((
                line_items[j]['x1'],
                line_items[j]['y1'],
                line_items[j]['x2'],
                line_items[j]['y2']
            ))

    if is_sensitive:
        redact_boxes.append((
            line['x1'],
            line['y1'],
            line['x2'],
            line['y2']
        ))

# =========================
# CHE THEO VÙNG OCR GỐC NẾU TỪ KHÓA BỊ TÁCH RIÊNG
# =========================

for item in ocr_items:
    norm = item['norm_text']

    if any(keyword in norm for keyword in sensitive_keywords):
        redact_boxes.append((
            item['x1'],
            item['y1'],
            item['x2'],
            item['y2']
        ))

# =========================
# GỘP VÙNG GẦN NHAU ĐỂ CHE KĨ HƠN
# =========================

# Mở rộng từng box để tránh sót chữ ở mép
expanded_boxes = []

img_h, img_w = img.shape[:2]

for x1, y1, x2, y2 in redact_boxes:
    expanded_boxes.append((
        max(0, x1 - 15),
        max(0, y1 - 10),
        min(img_w, x2 + 15),
        min(img_h, y2 + 10),
    ))

# =========================
# CHE ẢNH CHÂN DUNG NẾU BẬT
# =========================

if REDACT_FACE_AREA:
    redact_ratio_area(img, FACE_AREA_RATIO, padding=0)

# =========================
# VẼ CHE
# =========================

for x1, y1, x2, y2 in expanded_boxes:
    redact_rect(img, x1, y1, x2, y2, padding=0)

# =========================
# LƯU ẢNH
# =========================

cv2.imwrite(output_path, img)

print("\nĐã lưu ảnh che thông tin tại:")
print(output_path)
