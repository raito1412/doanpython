import cv2
import easyocr
import re
import unicodedata
import numpy as np
import tkinter as tk
from tkinter import messagebox
from vietocr.tool.predictor import Predictor
from vietocr.tool.config import Cfg
from PIL import Image

# =========================
# 1. KHỞI TẠO AI 1 LẦN DUY NHẤT LÚC IMPORT
# =========================
print("--- ĐANG NẠP MÔ HÌNH AI (EASYOCR + VIETOCR)... ---")
reader = easyocr.Reader(['vi', 'en'], gpu=False)
config = Cfg.load_config_from_name('vgg_transformer')
config['device'] = 'cpu' # Nếu máy không có card rời, đổi thành 'cpu'
vietocr_reader = Predictor(config)
print("--- NẠP MÔ HÌNH HOÀN TẤT ---")

# =========================
# 2. HÀM XỬ LÝ CHÍNH
# =========================
def process_and_redact(image_path, output_path, parent_window):
    """
    Hàm này nhận đầu vào là ảnh gốc, tự động OCR, mở menu chọn trên nền parent_window,
    và lưu ảnh đã che vào output_path.
    Trả về True nếu thành công, False nếu người dùng hủy.
    """
    img = cv2.imread(image_path)
    if img is None: 
        messagebox.showerror("Lỗi", f"Không đọc được ảnh: {image_path}", parent=parent_window)
        return False

    img_h, img_w = img.shape[:2]
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    max_size = 1200 
    scale_factor = max_size / max(gray_img.shape) if max(gray_img.shape) > max_size else 1.5
    
    gray_img = cv2.resize(gray_img, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
    blurred_img = cv2.GaussianBlur(gray_img, (3, 3), 0)

    print("🔍 AI đang quét tọa độ vùng chữ...")
    pre_results = reader.readtext(blurred_img)
    all_ocr_text = " ".join([res[1].lower() for res in pre_results])
    all_ocr_text = unicodedata.normalize('NFD', all_ocr_text)
    all_ocr_text = "".join([ch for ch in all_ocr_text if unicodedata.category(ch) != 'Mn']) 

    # --- LOGIC ĐỀ XUẤT ---
    suggested_face, suggested_barcode, suggested_finger, suggested_qr = False, False, False, False
    suggested_id_num, suggested_name, suggested_dob, suggested_address, suggested_cv_contact = False, False, False, False, False
    document_type = "Không xác định"

    if 'can cuoc' in all_ocr_text or 'citizen' in all_ocr_text:
        document_type = "Căn cước công dân"
        suggested_face = suggested_barcode = suggested_finger = suggested_qr = suggested_id_num = suggested_name = suggested_dob = suggested_address = True
    elif 'bao hiem y te' in all_ocr_text or 'bhyt' in all_ocr_text:
        document_type = "Thẻ Bảo hiểm y tế"
        suggested_id_num = suggested_name = suggested_dob = suggested_barcode = True
    elif 'sinh vien' in all_ocr_text or 'student' in all_ocr_text:
        document_type = "Thẻ sinh viên"
        suggested_id_num = suggested_name = suggested_barcode = suggested_face = True
    elif any(kw in all_ocr_text for kw in ['ho so', 'cv', 'resume', 'email']):
        document_type = "CV / Hồ sơ cá nhân"
        suggested_face = suggested_cv_contact = True

    # --- POPUP MENU (DÙNG TOPLEVEL THAY VÌ TK) ---
    user_choices = {}
    dialog = tk.Toplevel(parent_window)
    dialog.title("AI: Tùy chỉnh che thông tin")
    dialog.geometry("460x500")
    dialog.configure(bg="#F0F7F4")
    dialog.transient(parent_window) # Đặt cửa sổ này đè lên app chính
    dialog.grab_set() # Khóa tương tác app chính cho đến khi đóng hộp thoại

    var_face = tk.BooleanVar(value=suggested_face)
    var_barcode = tk.BooleanVar(value=suggested_barcode)
    var_finger = tk.BooleanVar(value=suggested_finger)
    var_qr = tk.BooleanVar(value=suggested_qr)
    var_id_num = tk.BooleanVar(value=suggested_id_num)    
    var_name = tk.BooleanVar(value=suggested_name)      
    var_dob = tk.BooleanVar(value=suggested_dob)       
    var_address = tk.BooleanVar(value=suggested_address)   
    var_cv_contact = tk.BooleanVar(value=suggested_cv_contact)

    tk.Label(dialog, text=f"🔍 AI nhận diện: {document_type}", bg="#E8F1F5", font=("Arial", 11, "italic")).pack(pady=10)

    # ... (Giữ nguyên các đoạn code vẽ Checkbutton f1, f2 của bạn vào đây) ...
    f1 = tk.LabelFrame(dialog, text=" Vùng hình ảnh & Mã vạch ", bg="#F0F7F4")
    f1.pack(fill="x", padx=30, pady=5)
    tk.Checkbutton(f1, text="Che khuôn mặt", variable=var_face, bg="#F0F7F4").pack(anchor="w")
    tk.Checkbutton(f1, text="Che mã vạch", variable=var_barcode, bg="#F0F7F4").pack(anchor="w")
    
    f2 = tk.LabelFrame(dialog, text=" Thông tin văn bản (Chữ) ", bg="#F0F7F4")
    f2.pack(fill="x", padx=30, pady=5)
    tk.Checkbutton(f2, text="Che Số giấy tờ", variable=var_id_num, bg="#F0F7F4").pack(anchor="w")
    tk.Checkbutton(f2, text="Che Họ và tên", variable=var_name, bg="#F0F7F4").pack(anchor="w")
    tk.Checkbutton(f2, text="Che Ngày sinh", variable=var_dob, bg="#F0F7F4").pack(anchor="w")

    is_submitted = [False] # Dùng list để mutate bên trong hàm

    def on_submit():
        user_choices['face'] = var_face.get()
        user_choices['barcode'] = var_barcode.get()
        user_choices['finger'] = var_finger.get()
        user_choices['qr'] = var_qr.get()
        user_choices['id_num'] = var_id_num.get()
        user_choices['name'] = var_name.get()
        user_choices['dob'] = var_dob.get()
        user_choices['address'] = var_address.get()
        user_choices['cv_contact'] = var_cv_contact.get()
        is_submitted[0] = True
        dialog.destroy()

    tk.Button(dialog, text="Xác nhận và Xử lý", command=on_submit, bg="#A8DADC").pack(pady=15)
    
    parent_window.wait_window(dialog) # Code sẽ dừng ở đây chờ user bấm nút

    if not is_submitted[0]:
        return False # User bấm X tắt cửa sổ

    REDACT_FACE_AREA = user_choices['face']
    REDACT_BARCODE = user_choices['barcode']
    REDACT_FINGERPRINT = user_choices['finger']
    REDACT_QR_CODE = user_choices['qr']
    REDACT_CV_CONTACT = user_choices.get('cv_contact', False)

    sensitive_keywords = []
    multi_line_keywords = []
    next_line_keywords = []
    vietnam_address_words = []

    if user_choices['id_num']:
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

    if user_choices.get('cv_contact'):
        sensitive_keywords.extend(['dien thoai', 'so dien thoai', 'phone', 'mobile', 'tel'])
        next_line_keywords.extend(['dien thoai', 'so dien thoai', 'phone', 'mobile', 'tel'])

    sensitive_keywords.extend(['dac diem nhan dang', 'personal identification', 'nhan dang'])
    multi_line_keywords.extend(['dac diem nhan dang', 'personal identification'])

    FACE_AREA_RATIO = {"x1": 0.03, "y1": 0.4, "x2": 0.30, "y2": 0.82}

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
        if roi.size == 0: return
        h, w = roi.shape[:2]
        temp = cv2.resize(roi, (blocks, blocks), interpolation=cv2.INTER_LINEAR)
        pixelated = cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)
        img[y1:y2, x1:x2] = pixelated

    def redact_barcode_area(img):
        img_h, img_w = img.shape[:2]
        x1 = int(img_w * 0.35)
        y1 = int(img_h * 0.83)
        x2 = int(img_w * 0.92)
        y2 = int(img_h * 0.98)
        pixelate_region(img, x1, y1, x2, y2, blocks=10)

    def redact_cv_portrait_area(img):
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

        if user_choices['id_num']:
            if re.fullmatch(r'[\d\s.-]{8,15}', text.strip()) and 8 <= len(digits_only) <= 12:
                return True
            if re.search(r'(?:\d[\s.-]?){12}', text) or re.search(r'(?:\d[\s.-]?){9}', text): return True
            if re.search(r'[a-zA-Z]{2}\d{10}', compact_text) or re.search(r'[A-Z]\d{7,8}', compact_text): return True
            if re.search(r'\d{10,13}', compact_text): return True
            if len(digits_only) in [9, 12]: return True

        if user_choices['dob']:
            if user_choices['dob']:
                sensitive_keywords.extend([
                'ngay sinh', 'sinh ngay', 'date of birth', 'dob', 
                'ngay cap', 'date of issue', 'ngay het han', 
                'co gia tri den', 'expiry', 'valid until', 'nam sinh:',
                # Thêm các từ khóa mới cho thẻ sinh viên
                'ngay vao truong', 'ngay sinh:', 'ngay/thang/nam sinh'
                ])
                next_line_keywords.extend(['ngay sinh', 'date of birth', 'ngay vao truong'])
            if re.search(r'\d{2}[\/\-.]\d{2}[\/\-.]\d{4}', text) or re.search(r'\d{4}[\/\-.]\d{2}[\/\-.]\d{2}', text): return True
            
        return False

    def redact_cv_contact_smart(img, ocr_items, line_items):
        img_h, img_w = img.shape[:2]
        left_col_limit = int(img_w * 0.45)
        email_pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z0-9]{2,}(?:\.[a-zA-Z0-9]{2,})*'
        phone_pattern = r'''(?<!\d)(?:(?:\+?84|0)[\s.-]?(?:\d[\s.-]?){8,10}|\d{3}[\s.-]?\d{3}[\s.-]?\d{4})(?!\d)'''

        def is_left_cv_item(item): return item['x1'] < left_col_limit

        def merge_boxes_local(boxes, distance_x=8, distance_y=8):
            if not boxes: return []
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
                if not added: merged.append(box)
            return merged

        def redact_email_rect(x1, y1, x2, y2):
            img_h, img_w = img.shape[:2]
            redact_rect(img, max(0, x1 - 3), max(0, y1 - 7), min(img_w, x2 + 3), min(img_h, y2 + 4), padding=0)

        def redact_email_match_in_items(items):
            items = [i for i in sorted(items, key=lambda k: k['x1']) if is_left_cv_item(i)]
            if not items: return False
            compact_text = ""
            parts = []
            for item in items:
                word = item['text'].strip()
                if not word: continue
                word_compact = re.sub(r'\s+', '', word)
                start = len(compact_text)
                compact_text += word_compact
                end = len(compact_text)
                parts.append({'item': item, 'start': start, 'end': end})

            found = False
            for match in re.finditer(email_pattern, compact_text):
                m_start, m_end = match.span()
                matched_items = [p['item'] for p in parts if p['end'] > m_start and p['start'] < m_end]
                if not matched_items: continue
                x1 = min(i['x1'] for i in matched_items)
                y1 = min(i['y1'] for i in matched_items)
                x2 = max(i['x2'] for i in matched_items)
                y2 = max(i['y2'] for i in matched_items)
                redact_email_rect(x1, y1, x2, y2)
                found = True
            return found

        def redact_phone_match_in_items(items):
            items = [i for i in sorted(items, key=lambda k: k['x1']) if is_left_cv_item(i)]
            if not items: return False
            compact_text = ""
            parts = []
            for item in items:
                word = item['text'].strip()
                if not word: continue
                word_compact = re.sub(r'\s+', '', word)
                start = len(compact_text)
                compact_text += word_compact
                end = len(compact_text)
                parts.append({'item': item, 'start': start, 'end': end})

            found = False
            for match in re.finditer(phone_pattern, compact_text, re.VERBOSE):
                m_start, m_end = match.span()
                matched_items = [p['item'] for p in parts if p['end'] > m_start and p['start'] < m_end]
                if not matched_items: continue
                x1 = min(i['x1'] for i in matched_items)
                y1 = min(i['y1'] for i in matched_items)
                x2 = max(i['x2'] for i in matched_items)
                y2 = max(i['y2'] for i in matched_items)
                redact_rect(img, x1, y1, x2, y2, padding=3)
                found = True
            return found

        for item in ocr_items:
            if not is_left_cv_item(item): continue
            text = item['text'].strip()
            if not text: continue
            if re.search(email_pattern, re.sub(r'\s+', '', text)): redact_email_rect(item['x1'], item['y1'], item['x2'], item['y2'])
            if re.search(phone_pattern, text, re.VERBOSE): redact_rect(img, item['x1'], item['y1'], item['x2'], item['y2'], padding=3)

        email_found_by_ocr = False
        for line in line_items:
            email_found_by_ocr = redact_email_match_in_items(line['items']) or email_found_by_ocr
            redact_phone_match_in_items(line['items'])

        email_label_lines = []
        for line in line_items:
            norm = line['norm_text']
            if re.search(r'\b(e\s*-?\s*mail|email|mail)\b', norm) and line['x1'] < left_col_limit:
                email_label_lines.append(line)

        next_section_keywords = ['so thich', 'hobbies', 'ky nang', 'skills', 'hoc van', 'education', 'kinh nghiem', 'experience', 'du an', 'projects']

        for email_line in email_label_lines:
            y_start = email_line['y2'] + 1
            y_end = min(img_h, y_start + int(img_h * 0.16))
            for line in line_items:
                if line['y1'] <= email_line['y2']: continue
                if line['x1'] >= left_col_limit: continue
                if any(k in line['norm_text'] for k in next_section_keywords):
                    y_end = min(y_end, max(y_start + 1, line['y1'] - 3))
                    break

            items_below = [item for item in ocr_items if is_left_cv_item(item) and item['y1'] >= y_start and item['y2'] <= y_end]
            if redact_email_match_in_items(items_below): continue

            x_start = max(0, email_line['x1'] - 2)
            x_end = left_col_limit
            if y_end <= y_start or x_end <= x_start: continue

            roi = img[y_start:y_end, x_start:x_end]
            if roi.size == 0: continue

            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            dark_mask = gray < 185
            saturated_mask = hsv[:, :, 1] > 35
            mask = (dark_mask | saturated_mask).astype(np.uint8) * 255
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 2))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
            kernel_join = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3))
            mask = cv2.dilate(mask, kernel_join, iterations=1)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            boxes = []
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                if w < 12 or h < 3: continue
                if h > (y_end - y_start) * 0.8: continue
                boxes.append((x_start + x, y_start + y, x_start + x + w, y_start + y + h))

            for x1, y1, x2, y2 in merge_boxes_local(boxes, distance_x=10, distance_y=6):
                redact_email_rect(x1, y1, x2, y2)

    # =========================
    # SỬ DỤNG LẠI KẾT QUẢ OCR ĐỂ GOM DÒNG VÀ VẼ CHE
    # =========================
    ocr_items = []
    print("\n===== NỘI DUNG OCR KẾT HỢP THÔNG MINH =====")
    for bbox, easy_text, conf in pre_results:
        x1, y1, x2, y2 = get_rect_from_bbox(bbox)
        
        # Thu hồi tọa độ về ảnh gốc bằng tỷ lệ scale_factor tự động
        x1, y1 = int(x1 / scale_factor), int(y1 / scale_factor)
        x2, y2 = int(x2 / scale_factor), int(y2 / scale_factor)
        
        easy_text_clean = easy_text.strip()
        if not easy_text_clean: 
            continue
        
        # --- BỘ LỌC THÔNG MINH: Ngăn VietOCR đọc bậy mã vạch/số ---
        # Nếu chứa ký tự MRZ (<<) hoặc toàn số, hoặc chữ tiếng Anh tự tin cao -> Dùng EasyOCR
        if '<<' in easy_text_clean or easy_text_clean.isdigit() or (conf > 0.85 and easy_text_clean.isupper()):
            final_text = easy_text_clean
        else:
            # Chỉ các từ nghi ngờ là tiếng Việt mới dùng VietOCR
            px1, py1 = max(0, x1 - 2), max(0, y1 - 2)
            px2, py2 = min(img_w, x2 + 2), min(img_h, y2 + 2)
            crop_img = img[py1:py2, px1:px2]
            
            if crop_img.shape[0] > 5 and crop_img.shape[1] > 5:
                pil_img = Image.fromarray(cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB))
                vietocr_text = vietocr_reader.predict(pil_img).strip()
                
                # Ngăn chặn lỗi lặp từ (VD: THỊ THỊ THỊ)
                words = vietocr_text.split()
                if len(words) > 3 and len(set(words)) < len(words) / 2:
                    final_text = easy_text_clean
                else:
                    final_text = vietocr_text if vietocr_text else easy_text_clean
            else:
                final_text = easy_text_clean

        item = {
            'text': final_text, 'norm_text': normalize_text(final_text), 'conf': conf,
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'center_y': (y1 + y2) // 2, 'height': y2 - y1,
        }
        ocr_items.append(item)
        print(final_text)

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
    # Regex tìm đúng định dạng ngày tháng
    date_pattern = r'\d{1,2}[\/\-.\s]+\d{1,2}[\/\-.\s]+\d{2,4}'
    # THÊM MỚI: Bổ sung 'ho ten', 'ho va ten', 'name' vào phanh khẩn cấp để bảo vệ nhãn
    stop_labels = ['ngay sinh', 'sinh ngay', 'date of birth', 'dob', 'nam sinh', 'nganh', 'khoa hoc', 'khoa', 'que quan', 'dia chi', 'gioi tinh', 'ho ten', 'ho va ten', 'name']

    for index, line in enumerate(line_items):
        is_sensitive = False
        norm = line['norm_text']
        text = line['text']

        # 1. Bỏ qua ngay lập tức các dòng thông tin chung
        ignore_keywords = ['het han', 'nganh', 'khoa hoc', 'nien khoa', 'truong dai hoc', 'the sinh vien']
        if any(kw in norm for kw in ignore_keywords):
            continue 

        # --- LÁ CHẮN BẢO VỆ NGÀY SINH (Nếu không tick chọn) ---
        if not user_choices['dob']:
            is_date_label = any(kw in norm for kw in ['ngay sinh', 'sinh ngay', 'date of birth', 'dob', 'nam sinh'])
            has_date_format = re.search(date_pattern, text)
            if is_date_label or has_date_format:
                continue

        # 2. Bỏ qua nếu là cụm từ an toàn (Quốc hiệu, Tiêu đề...)
        if is_safe_phrase(norm) and not line_has_sensitive_pattern(text): 
            continue

        # --- CHỈ CHE SỐ NGÀY SINH, GIỮ LẠI CHỮ "NGÀY SINH:" ---
        if user_choices['dob']:
            is_date_label_line = any(kw in norm for kw in ['ngay sinh', 'sinh ngay', 'date of birth', 'dob', 'nam sinh'])
            if is_date_label_line:
                matches = list(re.finditer(date_pattern, text))
                if matches:
                    for match in matches:
                        start_char, end_char = match.span()
                        char_width = (line['x2'] - line['x1']) / max(1, len(text))
                        sub_x1 = int(line['x1'] + (start_char * char_width))
                        sub_x2 = int(line['x1'] + (end_char * char_width))
                        redact_rect(img, sub_x1, line['y1'], sub_x2, line['y2'], padding=2)
                else: 
                    if has_keyword(norm, next_line_keywords):
                        for j in range(index + 1, min(index + 2, len(line_items))):  
                            redact_boxes.append((line_items[j]['x1'], line_items[j]['y1'], line_items[j]['x2'], line_items[j]['y2']))
                continue 

        # --- THÊM MỚI: CHỈ CHE TÊN, GIỮ LẠI CHỮ "HỌ VÀ TÊN:" ---
        if user_choices['name']:
            name_labels = ['ho va ten', 'ho ten', 'full name', 'name']
            if any(kw in norm for kw in name_labels):
                # Tìm đoạn chứa nhãn "Họ tên:" (Bao gồm cả dấu hai chấm nếu có)
                match = re.search(r'(ho va ten|ho ten|full name|name)\s*:?', norm)
                if match:
                    start_char = match.end()
                    total_chars = max(1, len(norm))
                    
                    # Kiểm tra xem tên thật có nằm cùng dòng với nhãn không
                    if start_char < total_chars - 1:
                        char_width = (line['x2'] - line['x1']) / total_chars
                        # Tính toán x1 mới: Nằm ngay sau chữ "Họ tên: "
                        sub_x1 = int(line['x1'] + (start_char * char_width))
                        
                        # Vẽ hộp che kéo dài từ sau chữ "Họ tên:" đến tận cuối dòng
                        redact_rect(img, sub_x1, line['y1'], line['x2'], line['y2'], padding=2)
                
                # Xử lý trường hợp nhãn nằm trên, tên thật rớt xuống dòng dưới
                for j in range(index + 1, min(index + 2, len(line_items))):  
                    next_norm = line_items[j]['norm_text']
                    next_text = line_items[j]['text']
                    if any(label in next_norm for label in stop_labels): break
                    if not user_choices['dob'] and re.search(date_pattern, next_text): break
                    redact_boxes.append((line_items[j]['x1'], line_items[j]['y1'], line_items[j]['x2'], line_items[j]['y2']))
                
                # Bắt buộc continue để ngắt luồng, tuyệt đối không cho AI bôi đen nguyên cả dòng
                continue

        # 3. Đánh giá mức độ nhạy cảm của các dòng khác (Mã số, Quê quán, Địa chỉ...)
        if line_has_sensitive_pattern(text): is_sensitive = True
        if has_keyword(norm, sensitive_keywords): is_sensitive = True
        if has_keyword(norm, vietnam_address_words) and len(norm) >= 8: is_sensitive = True

        # 4. CHỐNG CHE LAN (HỆ THỐNG PHANH GẤP)
        if has_keyword(norm, multi_line_keywords):
            for j in range(index + 1, min(index + 5, len(line_items))):
                next_norm = line_items[j]['norm_text']
                next_text = line_items[j]['text']
                
                if any(label in next_norm for label in stop_labels): break
                if not user_choices['dob'] and re.search(date_pattern, next_text): break
                
                redact_boxes.append((line_items[j]['x1'], line_items[j]['y1'], line_items[j]['x2'], line_items[j]['y2']))

        if has_keyword(norm, next_line_keywords):
            for j in range(index + 1, min(index + 2, len(line_items))):  
                next_norm = line_items[j]['norm_text']
                next_text = line_items[j]['text']
                
                if any(label in next_norm for label in stop_labels): break
                if not user_choices['dob'] and re.search(date_pattern, next_text): break
                
                redact_boxes.append((line_items[j]['x1'], line_items[j]['y1'], line_items[j]['x2'], line_items[j]['y2']))

        # 5. Lưu lại tọa độ để che toàn bộ dòng nếu bị đánh dấu nhạy cảm (Dành cho Quê quán, MSSV đứng một mình...)
        if is_sensitive:
            redact_boxes.append((line['x1'], line['y1'], line['x2'], line['y2']))
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
        left_anchors = ['ngon tro trai', 'left index', 'tro trai', 'ngon tro']
        right_anchors = ['ngon tro phai', 'right index', 'tro phai','ngon tro']
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
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml') #type: ignore
        gray_face = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        for (x, y, w, h) in face_cascade.detectMultiScale(gray_face, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)):
            pixelate_region(img, x, y, x + w, y + h, blocks=8)

        if document_type.startswith("CV"):
            redact_cv_portrait_area(img)
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
    
    # Giả lập ghi file (bạn dán code gốc thay thế dòng này)
    cv2.imwrite(output_path, img)
    print(f"\n✨ Xử lý hoàn tất! Đã lưu ảnh tại: {output_path}")
    return True