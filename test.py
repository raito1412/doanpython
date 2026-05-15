import cv2
import easyocr
import re
import unicodedata

image_path = 'anh_test.jpg'
output_path = 'cccd_redacted.jpg'

reader = easyocr.Reader(['vi', 'en'], gpu=False)

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

    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(img_w, x2 + padding)
    y2 = min(img_h, y2 + padding)

    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), -1)

img = cv2.imread(image_path)

if img is None:
    raise FileNotFoundError(
        f"Không đọc được ảnh: {image_path}. Hãy để ảnh cùng thư mục với test.py"
    )

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
        'x1': x1,
        'y1': y1,
        'x2': x2,
        'y2': y2,
        'center_y': (y1 + y2) // 2
    }

    ocr_items.append(item)
    print(text)

ocr_items = sorted(ocr_items, key=lambda item: (item['y1'], item['x1']))

lines = []

for item in ocr_items:
    added = False

    for line in lines:
        if abs(item['center_y'] - line['center_y']) < 18:
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
        'y2': y2
    })

line_items = sorted(line_items, key=lambda item: item['y1'])

print("\n===== NỘI DUNG OCR THEO DÒNG =====")

for line in line_items:
    print(line['text'])

patterns = [
    r'(?:\d[\s.-]?){12}',
    r'\d{2}[\/\-.]\d{2}[\/\-.]\d{4}',
]

sensitive_keywords = [
    
    'ngay sinh',
    'sinh ngay',
    'date of birth',
    'dob',
    'gioi tinh',
    'sex',
    'quoc tich',
    'nationality',
    'que quan',
    'place of origin',
    'noi thuong tru',
    'thuong tru',
    'place of residence',
    'dia chi',
    'noi o hien tai',
    'TP HCM'
]

address_keywords = [
    'que quan',
    'place of origin',
    'noi thuong tru',
    'thuong tru',
    'place of residence',
    'dia chi',
    'noi o hien tai',
    'TP HCM'
    'Viet Nam'
]

address_anchor_y_list = []

for line in line_items:
    is_sensitive = False

    for pattern in patterns:
        if re.search(pattern, line['text']):
            is_sensitive = True

    digits_only = re.sub(r'\D', '', line['text'])

    if len(digits_only) >= 9:
        is_sensitive = True

    if any(keyword in line['norm_text'] for keyword in sensitive_keywords):
        is_sensitive = True

    if any(keyword in line['norm_text'] for keyword in address_keywords):
        address_anchor_y_list.append(line['y1'])

    if is_sensitive:
        redact_rect(
            img,
            line['x1'],
            line['y1'],
            line['x2'],
            line['y2']
        )

for anchor_y in address_anchor_y_list:
    for line in line_items:
        if anchor_y <= line['y1'] <= anchor_y + 190:
            redact_rect(
                img,
                line['x1'],
                line['y1'],
                line['x2'],
                line['y2']
            )

cv2.imwrite(output_path, img)

print("\nĐã lưu ảnh che thông tin tại:")
print(output_path)
