import cv2
import easyocr
import re
import unicodedata
import numpy as np

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

# Bật/tắt phát hiện mã vạch và dấu vân tay (THÊM MỚI)
REDACT_BARCODE = True
REDACT_FINGERPRINT = True

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

def keyword_in_text(text, keywords):
    for keyword in keywords:
        if re.search(r'\b' + re.escape(keyword) + r'\b', text, flags=re.IGNORECASE):
            return True
    return False

def keyword_in_text(text, keywords):
    for keyword in keywords:
        if re.search(r'\b' + re.escape(keyword) + r'\b', text, flags=re.IGNORECASE):
            return True
    return False

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

def preprocess_for_qr(gray):

    versions = []

    # ảnh gốc
    versions.append(gray)

    # sharpen nhẹ
    blur = cv2.GaussianBlur(gray, (0, 0), 2)

    sharpen = cv2.addWeighted(
        gray,
        1.3,
        blur,
        -0.3,
        0
    )

    versions.append(sharpen)

    return versions
# PHÁT HIỆN QR CODE 
# =========================
# QR CODE DETECTION 
# =========================

def detect_qr_opencv(img, detector):

    qr_boxes = []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # sharpen nhẹ để tăng detect QR nhỏ
    blur = cv2.GaussianBlur(gray, (0, 0), 2)

    sharpen = cv2.addWeighted(
        gray,
        1.3,
        blur,
        -0.3,
        0
    )

    # chỉ dùng 2 phiên bản để tăng tốc
    processed_images = [
        gray,
        sharpen
    ]

    # scale vừa đủ mạnh nhưng vẫn nhanh
    scales = [1.0, 2.0]

    for proc in processed_images:

        for scale in scales:

            resized = cv2.resize(
                proc,
                None,
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_LINEAR
            )

            try:

                retval, points = detector.detectMulti(resized)

                if retval and points is not None:

                    for qr_points in points:

                        # scale ngược lại
                        qr_points = qr_points / scale

                        xs = [p[0] for p in qr_points]
                        ys = [p[1] for p in qr_points]

                        x1 = int(min(xs))
                        y1 = int(min(ys))
                        x2 = int(max(xs))
                        y2 = int(max(ys))

                        # lọc box quá nhỏ / lỗi
                        w = x2 - x1
                        h = y2 - y1

                        if w < 20 or h < 20:
                            continue

                        qr_boxes.append((x1, y1, x2, y2))

            except:
                pass

    return qr_boxes


# =========================
# GỘP QR GẦN NHAU
# =========================

def merge_nearby_boxes(boxes, distance=5):

    if not boxes:
        return []

    merged = []

    used = [False] * len(boxes)

    for i in range(len(boxes)):

        if used[i]:
            continue

        x1, y1, x2, y2 = boxes[i]

        used[i] = True

        changed = True

        while changed:

            changed = False

            for j in range(len(boxes)):

                if used[j]:
                    continue

                xx1, yy1, xx2, yy2 = boxes[j]

                if (
                    xx1 <= x2 + distance and
                    xx2 >= x1 - distance and
                    yy1 <= y2 + distance and
                    yy2 >= y1 - distance
                ):

                    x1 = min(x1, xx1)
                    y1 = min(y1, yy1)
                    x2 = max(x2, xx2)
                    y2 = max(y2, yy2)

                    used[j] = True
                    changed = True

        merged.append((x1, y1, x2, y2))

    return merged


# =========================
# PHÁT HIỆN + CHE QR
# =========================

def detect_and_redact_codes(img):

    qr_detector = cv2.QRCodeDetector()

    qr_boxes = detect_qr_opencv(img, qr_detector)

    # gộp box
    qr_boxes = merge_nearby_boxes(
        qr_boxes,
        distance=5
    )

    for x1, y1, x2, y2 in qr_boxes:

        # che gọn sát QR
        padding = 1

        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(img.shape[1], x2 + padding)
        y2 = min(img.shape[0], y2 + padding)

        pixelate_region(
            img,
            x1,
            y1,
            x2,
            y2,
            blocks=8
        )

        print(f"[QR DETECTED & REDACTED] {x1}, {y1}, {x2}, {y2}")
        
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
    'Date of expiry',
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
    'Date of expiry',
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
# THÊM MỚI: PHÁT HIỆN MÃ VẠCH (BARCODE)
# =========================

def detect_barcodes(img):
    """Phát hiện mã vạch trong ảnh sử dụng OpenCV"""
    barcode_boxes = []
    img_h, img_w = img.shape[:2]
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(grad_x, grad_y)
    magnitude = cv2.convertScaleAbs(magnitude)
    
    blurred = cv2.GaussianBlur(magnitude, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 50, 255, cv2.THRESH_BINARY)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for contour in contours:
        area = cv2.contourArea(contour)
        
        if area < 300 or area > 15000:
            continue
        
        x, y, w, h = cv2.boundingRect(contour)
        
        # Không che vùng quá lớn
        if w > img_w * 0.3 or h > img_h * 0.3:
            continue
        
        aspect_ratio = w / h if h > 0 else 0
        
        if (aspect_ratio > 2.5 or aspect_ratio < 0.4) and area < 12000:
            padding = 5
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(img.shape[1], x + w + padding)
            y2 = min(img.shape[0], y + h + padding)
            barcode_boxes.append((x1, y1, x2, y2))
            print(f"[BARCODE] area={area:.0f}, ratio={aspect_ratio:.2f}")
    
    barcode_boxes = merge_nearby_boxes(barcode_boxes, distance=10)
    
    if len(barcode_boxes) > 3:
        barcode_boxes = barcode_boxes[:3]
    
    return barcode_boxes

# =========================
# THÊM MỚI: PHÁT HIỆN DẤU VÂN TAY (FINGERPRINT)
# =========================

def detect_fingerprints(img):
    """Phát hiện dấu vân tay trong ảnh"""
    fingerprint_boxes = []
    img_h, img_w = img.shape[:2]
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    sobelx = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)
    gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
    gradient_magnitude = cv2.convertScaleAbs(gradient_magnitude)
    
    _, thresh = cv2.threshold(gradient_magnitude, 30, 255, cv2.THRESH_BINARY)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for contour in contours:
        area = cv2.contourArea(contour)
        
        if area < 300 or area > 6000:
            continue
        
        x, y, w, h = cv2.boundingRect(contour)
        
        # Không che vùng quá lớn
        if w > img_w * 0.2 or h > img_h * 0.2:
            continue
        
        roi = thresh[y:y+h, x:x+w]
        density = np.sum(roi > 0) / (w * h) if w * h > 0 else 0
        
        if 0.2 < density < 0.7:
            padding = 8
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(img.shape[1], x + w + padding)
            y2 = min(img.shape[0], y + h + padding)
            fingerprint_boxes.append((x1, y1, x2, y2))
            print(f"[FINGERPRINT] area={area:.0f}, density={density:.2f}")
    
    fingerprint_boxes = merge_nearby_boxes(fingerprint_boxes, distance=20)
    
    if len(fingerprint_boxes) > 4:
        fingerprint_boxes = fingerprint_boxes[:4]
    
    return fingerprint_boxes

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
# THÊM MỚI: PHÁT HIỆN MÃ VẠCH
# =========================

if REDACT_BARCODE:
    print("\n[BARCODE DETECTION] Đang phát hiện mã vạch...")
    barcode_boxes = detect_barcodes(img)
    if barcode_boxes:
        for x1, y1, x2, y2 in barcode_boxes:
            pixelate_region(img, x1, y1, x2, y2, blocks=12)
            print(f"[BARCODE REDACTED] ({x1}, {y1}) -> ({x2}, {y2})")
    else:
        print("[BARCODE DETECTION] Không tìm thấy mã vạch")

# =========================
# THÊM MỚI: PHÁT HIỆN DẤU VÂN TAY
# =========================

if REDACT_FINGERPRINT:
    print("\n[FINGERPRINT DETECTION] Đang phát hiện dấu vân tay...")
    fingerprint_boxes = detect_fingerprints(img)
    if fingerprint_boxes:
        for x1, y1, x2, y2 in fingerprint_boxes:
            pixelate_region(img, x1, y1, x2, y2, blocks=10)
            print(f"[FINGERPRINT REDACTED] ({x1}, {y1}) -> ({x2}, {y2})")
    else:
        print("[FINGERPRINT DETECTION] Không tìm thấy dấu vân tay")

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
        if abs(item['center_y'] - line['center_y']) < max(6, avg_height * 0.45):
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
# XÁC ĐỊNH & CHE THÔNG TIN NHẠY CẢM 
# =========================

redact_boxes = []
pending_label = None

for line in line_items:
    original_text = line['text']
    norm_text = line['norm_text']
    x1, y1, x2, y2 = line['x1'], line['y1'], line['x2'], line['y2']
    if pending_label:
        redact_boxes.append((x1, y1, x2, y2))
        print(f"[REDACT NEXT LINE] {original_text}")

        pending_label = None
        continue
    # Bỏ qua tiêu đề lớn của giấy tờ
    TITLE_WORDS = [
    'can cuoc',
    'can cuoc cong dan',
    'citizen identity',
    'citizen identity card',
    'cong hoa xa hoi chu nghia viet nam',
    'doc lap tu do hanh phuc',
    'the sinh vien',
    'student card',
    'ho chieu'
    ]

    is_title = any(phrase in norm_text for phrase in TITLE_WORDS)
    has_label_separator = ':' in original_text or '：' in original_text

    if is_title and not has_label_separator:
        continue
    # === Tách Label và Value ===
    label = original_text
    value = ""
    value_x1 = x1

    if ':' in original_text:
        parts = [p.strip() for p in original_text.split(':', 1)]
        label = parts[0] + ":"
        value = parts[1] if len(parts) > 1 else ""
        label_char_ratio = len(label) / max(len(original_text), 1)
        label_width = int((x2 - x1) * max(0.40, min(label_char_ratio, 0.65)))
        value_x1 = x1 + label_width

    elif '：' in original_text:
        parts = [p.strip() for p in original_text.split('：', 1)]
        label = parts[0] + "："
        value = parts[1] if len(parts) > 1 else ""
        value_x1 = x1 + int((x2 - x1) * 0.45)

    else:
        # Không có dấu :, thử tách theo từ khóa
        for kw in next_line_keywords + ['so cccd', 'cccd', 'cmnd', 'ho ten', 'ho va ten']:
            if kw in norm_text:
                match = re.search(re.escape(kw.replace(' ', '.*?')), original_text, re.IGNORECASE)
                if match:
                    value_start_pos = match.end()
                    label = original_text[:value_start_pos].strip()
                    value = original_text[value_start_pos:].strip()
                    value_x1 = x1 + int((len(label) / len(original_text)) * (x2 - x1)) + 8
                    break

    # === QUYẾT ĐỊNH CHE ===
    should_redact = False

    if value:
        digits = re.sub(r'\D', '', value)
        norm_value = normalize_text(value)

        if ("ho va ten" in norm_text or "ho ten" in norm_text ) or \
           (len(digits) >= 8) or \
           line_has_sensitive_pattern(value) or \
           any(word in norm_value for word in vietnam_address_words):                                     
            should_redact = True

    # Nếu là dòng "Họ và tên" thì che luôn cả value
    if any(k in norm_text for k in ['ho va ten', 'ho ten', 'full name', 'name']):
        pending_label = True
        value_x1 = x1 + int((x2 - x1) * 0.65)   # che từ giữa dòng trở đi
    # Nếu là dòng "Giới tính" 
    if any(k in norm_text for k in ['gioi tinh', 'sex', 'gender']):
        should_redact = True
        value_x1 = x1 + int((x2 - x1) * 0.40)

    if any(k in norm_text for k in ['que quan', 'place of origin', 'noi sinh', 'place of birth']):
        pending_label = True
        value_x1 = x1 + int((x2 - x1) * 0.65)

    if any(k in norm_text for k in ['quoc tich', 'nationality']):
        should_redact = True
        value_x1 = x1 + int((x2 - x1) * 0.75)

    if any(k in norm_text for k in ['noi thuong tru', 'thuong tru', 'place of residence', 'residence', 'dia chi', 'address']):
        pending_label = True
        value_x1 = x1 + int((x2 - x1) * 0.70)

    if any(k in norm_text for k in ['dan toc', 'ton giao', 'religion']):
        should_redact = True
        value_x1 = x1 + int((x2 - x1) * 0.45)

    if any(k in norm_text for k in ['ngay sinh', 'date of birth', 'sinh ngay']):
        should_redact = True
        value_x1 = x1 + int((x2 - x1) * 0.65)

    if any(k in norm_text for k in ['co gia tri den', 'ngay het han', 'expiry', 'date of expiry', 'valid until']):
        pending_label = True
        value_x1 = x1 + int((x2 - x1) * 0.90)

    if should_redact and value_x1 < x2 - 10:
        value_width = int((x2 - value_x1) * 0.9)  
        redact_boxes.append((
            value_x1,
            y1 - 4,
            value_x1 + value_width,
            y2 + 4
        ))
        print(f"[REDACT] \"{label}\" → \"{value}\"")
    elif line_has_sensitive_pattern(original_text) and len(value) < 5:
        split_x = x1 + int((x2 - x1) * 0.2)  # giữ ~40% đầu làm label
        redact_boxes.append((split_x, y1 - 10, x2 + 6, y2 + 8))
        print(f"[REDACT VALUE ONLY] {original_text}")

# MỞ RỘNG VÙNG CHE 
expanded_boxes = []

img_h, img_w = img.shape[:2]

for x1, y1, x2, y2 in redact_boxes:
    expanded_boxes.append((
        max(0, x1 - 8),
        max(0, y1 - 10),
        min(img_w, x2 + 8),
        min(img_h, y2 + 8),
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

# =========================
# CHE DẤU VÂN TAY THEO VÙNG CỐ ĐỊNH (ĐÃ TỐI ƯU CHO MẶT SAU CCCD)
# =========================

if REDACT_FINGERPRINT:
    print("\n[FINGERPRINT FIXED] Đang làm mờ cả 2 dấu vân tay trên CCCD...")
    
    img_h, img_w = img.shape[:2]
    
    # Tọa độ được căn chỉnh để che toàn bộ góc trên bên phải (bao gồm cả 2 ô vân tay)
    fingerprint_region = {
        "x1": 0.49,   # Bắt đầu từ giữa thẻ dịch sang phải để che trọn ô vân tay trái
        "y1": 0.12,   # Đẩy sát lên cạnh trên cùng của ô vân tay
        "x2": 0.82,   # Kéo dài sang phải vừa đủ bao hết ô vân tay phải
        "y2": 0.46,   # Kéo xuống dưới để phủ hết chiều dọc của cả 2 ô
    }
    
    # Tính toán tọa độ pixel thực tế trên ảnh
    x1 = int(img_w * fingerprint_region["x1"])
    y1 = int(img_h * fingerprint_region["y1"])
    x2 = int(img_w * fingerprint_region["x2"])
    y2 = int(img_h * fingerprint_region["y2"])
    
    # Tiến hành làm mờ (pixelate) với độ mờ mạnh (blocks=6 để xóa hoàn toàn cấu trúc vân)
    pixelate_region(img, x1, y1, x2, y2, blocks=6)
    print(f"[FINGERPRINT FIXED] Đã che hoàn toàn vân tay tại vùng ({x1}, {y1}) -> ({x2}, {y2})")

# =========================
# CHE MÃ VẠCH THEO VÙNG CỐ ĐỊNH (ĐÃ TỐI ƯU CHO THẺ SGU)
# =========================

if REDACT_BARCODE:
    print("\n[BARCODE FIXED] Đang làm mờ toàn bộ mã vạch...")
    
    img_h, img_w = img.shape[:2]
    
    # Tọa độ đã được mở rộng để ôm trọn mã vạch từ trái sang phải ở góc dưới thẻ
    barcode_region = {
        "x1": 0.33,   # Bắt đầu dịch sang trái một chút để sát mép đầu mã vạch
        "y1": 0.81,   # Đẩy dịch lên trên để không bị sót phần đỉnh các vạch đen
        "x2": 0.89,   # Kéo dài sang phải để che hết cả phần mờ pixel cũ
        "y2": 0.94,   # Kéo xuống sát đáy mã vạch
    }
    
    # Tính toán tọa độ pixel thực tế trên ảnh
    x1 = int(img_w * barcode_region["x1"])
    y1 = int(img_h * barcode_region["y1"])
    x2 = int(img_w * barcode_region["x2"])
    y2 = int(img_h * barcode_region["y2"])
    
    # Tiến hành làm mờ (pixelate) với độ mờ mạnh (blocks=6 để nhòe hẳn)
    pixelate_region(img, x1, y1, x2, y2, blocks=12)
    print(f"[BARCODE FIXED] Đã che hoàn toàn mã vạch tại vùng ({x1}, {y1}) -> ({x2}, {y2})")

cv2.imwrite(output_path, img)

print("\nĐã lưu ảnh che thông tin tại:")
print(output_path)
    # Tính toán tọa độ pixel thực tế trên ảnh
x1 = int(img_w * barcode_region["x1"])
y1 = int(img_h * barcode_region["y1"])
x2 = int(img_w * barcode_region["x2"])
y2 = int(img_h * barcode_region["y2"])
    
    # Tiến hành làm mờ (pixelate) với độ mờ mạnh (blocks=6 để nhòe hẳn)
pixelate_region(img, x1, y1, x2, y2, blocks=12)
print(f"[BARCODE FIXED] Đã che hoàn toàn mã vạch tại vùng ({x1}, {y1}) -> ({x2}, {y2})")

cv2.imwrite(output_path, img)

print("\nĐã lưu ảnh che thông tin tại:")
print(output_path)