import os
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

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG & AI GLOBAL (LAZY LOAD)
# ==========================================
AI_MODELS = {'easyocr': None, 'vietocr': None}

def get_ai_models():
    """Hàm tải mô hình AI vào VRAM (Chỉ tải 1 lần duy nhất)"""
    if AI_MODELS['easyocr'] is None:
        print("\n--- ĐANG NẠP MÔ HÌNH AI (EASYOCR + VIETOCR)... ---")
        # Đổi gpu=False nếu chạy máy không có card rời, gpu=True nếu có card
        AI_MODELS['easyocr'] = easyocr.Reader(['vi', 'en'], gpu=True)
        
        config = Cfg.load_config_from_name('vgg_transformer')
        # Tùy cấu hình máy: dùng 'cuda:0' cho card rời NVIDIA, 'cpu' cho máy thường
        config['device'] = 'cpu' 
        AI_MODELS['vietocr'] = Predictor(config)
        print("--- NẠP MÔ HÌNH THÀNH CÔNG! ---")
    return AI_MODELS['easyocr'], AI_MODELS['vietocr']

# ==========================================
# 2. HÀM XỬ LÝ CHÍNH 
# ==========================================
def process_and_redact(image_path, output_path, parent_window):
    """
    Hàm này nhận đầu vào là ảnh gốc, tự động OCR, mở menu chọn trên nền parent_window,
    và lưu ảnh đã che vào output_path.
    Trả về True nếu thành công, False nếu người dùng hủy hoặc lỗi.
    """
    reader, vietocr_reader = get_ai_models()
    
    # --- 1. ĐỌC ẢNH HỖ TRỢ ĐƯỜNG DẪN TIẾNG VIỆT ---
    try:
        img_array = np.fromfile(image_path, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if img is None:
            # Fallback dùng PIL nếu OpenCV không đọc được
            pil_img = Image.open(image_path).convert('RGB')
            img = np.array(pil_img)
            img = img[:, :, ::-1].copy() 

    except Exception as e:
        messagebox.showerror("Lỗi định dạng", f"Không thể đọc file này như một bức ảnh.\nChi tiết: {str(e)}", parent=parent_window)
        return False

    if img is None: 
        messagebox.showerror("Lỗi định dạng", f"Hệ thống không nhận diện được file này là ảnh.", parent=parent_window)
        return False

    img_h, img_w = img.shape[:2]

    # --- 2. TIỀN XỬ LÝ ẢNH DÀNH CHO OCR ---
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray_img.shape
    max_size = 1200 
    scale_factor = max_size / max(h, w) if max(h, w) > max_size else 1.5
    
    gray_img = cv2.resize(gray_img, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
    blurred_img = cv2.GaussianBlur(gray_img, (3, 3), 0)

    print("🔍 AI đang quét tọa độ vùng chữ...")
    pre_results = reader.readtext(blurred_img)

    print("🔍 AI đang phân tích loại giấy tờ để đưa ra đề xuất...")
    all_ocr_text = " ".join([res[1].lower() for res in pre_results])
    all_ocr_text = unicodedata.normalize('NFD', all_ocr_text)
    all_ocr_text = "".join([ch for ch in all_ocr_text if unicodedata.category(ch) != 'Mn'])

    # --- 3. LOGIC AI ĐỀ XUẤT TỰ ĐỘNG ---
    suggestions = {
        'face': False, 'barcode': False, 'finger': False, 'qr': False,
        'id_num': False, 'name': False, 'dob': False, 'address': False, 'cv_contact': False, 'plate': False
    }
    document_type = "Không xác định (Tự chọn)"

    if 'can cuoc' in all_ocr_text or 'citizen' in all_ocr_text:
        document_type = "Căn cước công dân (Mặt trước)"
        suggestions.update({'face': True, 'barcode': False, 'finger': False, 'qr': True, 'id_num': True, 'name': True, 'dob': True, 'address': True})
    elif 'dac diem nhan dang' in all_ocr_text or 'personal identification' in all_ocr_text:
        document_type = "Căn cước công dân (Mặt sau)"
        suggestions.update({'finger': True, 'id_num': True, 'name': True})
    elif 'bao hiem y te' in all_ocr_text or 'bhyt' in all_ocr_text or 'the bhyt' in all_ocr_text:
        document_type = "Thẻ Bảo hiểm y tế"
        suggestions.update({'id_num': True, 'name': True, 'dob': True, 'barcode': True})
    elif 'sinh vien' in all_ocr_text or 'student' in all_ocr_text:
        document_type = "Thẻ sinh viên / Thẻ học sinh"
        suggestions.update({'id_num': True, 'name': True, 'barcode': True, 'face': True})
    elif any(k in all_ocr_text for k in ['ho so', 'cv', 'resume', 'lien he', 'email', 'dien thoai', 'hoc van', 'kinh nghiem', 'ky nang']):
        document_type = "CV / Hồ sơ cá nhân"
        suggestions.update({'face': True, 'cv_contact': True})

    if document_type == "Không xác định (Tự chọn)":
        document_type = "Ảnh thường / Ảnh chung"
        suggestions.update({'face': True, 'cv_contact': True})

    print(f"📌 AI ĐỀ XUẤT: [{document_type}]")

    # --- 4. GIAO DIỆN XÁC NHẬN (TOPLEVEL) ---
    user_choices = {}
    is_submitted = [False]
    
    dialog = tk.Toplevel(parent_window)
    dialog.title("Hệ thống che thông tin AI")
    dialog.geometry("460x500")
    dialog.configure(bg="#F0F7F4")
    dialog.transient(parent_window)
    dialog.grab_set()
    
    var_face = tk.BooleanVar(value=suggestions['face'])
    var_barcode = tk.BooleanVar(value=suggestions['barcode'])
    var_finger = tk.BooleanVar(value=suggestions['finger'])
    var_qr = tk.BooleanVar(value=suggestions['qr'])
    var_id_num = tk.BooleanVar(value=suggestions['id_num'])    
    var_name = tk.BooleanVar(value=suggestions['name'])      
    var_dob = tk.BooleanVar(value=suggestions['dob'])       
    var_address = tk.BooleanVar(value=suggestions['address'])   
    var_cv_contact = tk.BooleanVar(value=suggestions['cv_contact'])
    var_plate = tk.BooleanVar(value=suggestions['plate'])

    tk.Label(dialog, text=f"🔍 AI nhận diện: {document_type}", bg="#E8F1F5", fg="#1D3557", font=("Arial", 11, "italic"), bd=1, relief="solid", padx=10, pady=5).pack(fill="x", padx=30, pady=(15, 5))
    tk.Label(dialog, text="🛠️ ĐIỀU CHỈNH VÙNG CẦN CHE:", bg="#F0F7F4", fg="#2C3E50", font=("Arial", 11, "bold")).pack(pady=5)

    f1 = tk.LabelFrame(dialog, text=" Vùng hình ảnh & Mã vạch ", bg="#F0F7F4", font=("Arial", 10, "bold"), padx=10, pady=5)
    f1.pack(fill="x", padx=30, pady=5)
    tk.Checkbutton(f1, text="Che khuôn mặt", variable=var_face, bg="#F0F7F4").pack(anchor="w", padx=20)
    tk.Checkbutton(f1, text="Che mã vạch", variable=var_barcode, bg="#F0F7F4").pack(anchor="w", padx=20)
    tk.Checkbutton(f1, text="Che dấu vân tay", variable=var_finger, bg="#F0F7F4").pack(anchor="w", padx=20)
    tk.Checkbutton(f1, text="Che mã QR", variable=var_qr, bg="#F0F7F4").pack(anchor="w", padx=20)

    f2 = tk.LabelFrame(dialog, text=" Thông tin văn bản ", bg="#F0F7F4", font=("Arial", 10, "bold"), padx=10, pady=5)
    f2.pack(fill="x", padx=30, pady=5)
    tk.Checkbutton(f2, text="Che Số định danh/Số thẻ", variable=var_id_num, bg="#F0F7F4").pack(anchor="w", padx=20)
    tk.Checkbutton(f2, text="Che Họ và tên", variable=var_name, bg="#F0F7F4").pack(anchor="w", padx=20)
    tk.Checkbutton(f2, text="Che Ngày sinh", variable=var_dob, bg="#F0F7F4").pack(anchor="w", padx=20)
    tk.Checkbutton(f2, text="Che Địa chỉ", variable=var_address, bg="#F0F7F4").pack(anchor="w", padx=20)
    tk.Checkbutton(f2, text="Che Email / Số điện thoại tự do", variable=var_cv_contact, bg="#F0F7F4").pack(anchor="w", padx=20)
    tk.Checkbutton(f1, text="Che biển số xe", variable=var_plate, bg="#F0F7F4").pack(anchor="w", padx=20)

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
        user_choices['plate'] = var_plate.get()
        is_submitted[0] = True
        dialog.destroy()

    tk.Button(dialog, text="Xác nhận và Xử lý ảnh", command=on_submit, bg="#A8DADC", fg="#1D3557", font=("Arial", 11, "bold"), padx=25, pady=5, cursor="hand2").pack(pady=15)
    
    parent_window.wait_window(dialog)

    if not is_submitted[0]:
        print("Đã hủy thao tác xử lý ảnh.")
        return False

    # --- 5. SETUP TỪ KHÓA TÌM KIẾM ---
    sensitive_keywords, multi_line_keywords, next_line_keywords, vietnam_address_words = [], [], [], []

    if user_choices['id_num']:
        sensitive_keywords.extend(['so', 'so the', 'so cccd', 'so ho chieu', 'ma so thue', 'mst', 'so bhxh', 'so bhyt', 'ma so', 'ma the', 'no'])
    if user_choices['name']:
        sensitive_keywords.extend(['ho va ten', 'ho ten', 'ten', 'full name', 'name', 'ho ten:'])
        next_line_keywords.extend(['ho va ten', 'ho ten', 'full name', 'name'])
    if user_choices['dob']:
        sensitive_keywords.extend(['ngay sinh', 'sinh ngay', 'date of birth', 'dob', 'ngay cap', 'date of issue', 'ngay het han', 'co gia tri den', 'expiry', 'valid until', 'nam sinh:', 'ngay vao truong', 'ngay sinh:', 'ngay/thang/nam sinh'])
        next_line_keywords.extend(['ngay sinh', 'date of birth', 'ngay cap', 'ngay het han', 'expiry', 'co gia tri den', 'ngay vao truong'])
    if user_choices['address']:
        sensitive_keywords.extend(['que quan', 'place of origin', 'noi sinh', 'place of birth', 'noi thuong tru', 'thuong tru', 'place of residence', 'residence', 'dia chi', 'address', 'noi o hien tai', 'noi dki kcb ban dau', 'noi dk kcb'])
        multi_line_keywords.extend(['que quan', 'place of origin', 'noi sinh', 'place of birth', 'noi thuong tru', 'thuong tru', 'place of residence', 'residence', 'dia chi', 'address', 'noi o hien tai', 'noi dki kcb ban dau'])
        vietnam_address_words.extend(['tp hcm', 'tphcm', 'ho chi minh', 'ha noi', 'da nang', 'can tho', 'hai phong', 'binh duong', 'dong nai', 'long an', 'ba ria', 'vung tau', 'quan', 'huyen', 'thi xa', 'thanh pho', 'phuong', 'xa', 'thi tran', 'ap', 'thon', 'khu pho', 'duong', 'so nha'])
    if user_choices['cv_contact']:
        sensitive_keywords.extend(['dien thoai', 'so dien thoai', 'phone', 'mobile', 'tel'])
        next_line_keywords.extend(['dien thoai', 'so dien thoai', 'phone', 'mobile', 'tel'])

    sensitive_keywords.extend(['dac diem nhan dang', 'personal identification', 'nhan dang'])
    multi_line_keywords.extend(['dac diem nhan dang', 'personal identification'])

    # ==========================================
    # HÀM HỖ TRỢ VẼ/CHE MỜ (NESTED FUNCTIONS)
    # ==========================================
    def remove_accents(text):
        return ''.join(ch for ch in unicodedata.normalize('NFD', text) if unicodedata.category(ch) != 'Mn')
    
    def normalize_text(text):
        return re.sub(r'\s+', ' ', remove_accents(text).lower()).strip()
    
    def has_keyword(norm_text, keywords):
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', norm_text): return True
        return False

    def redact_rect(img_ref, x1, y1, x2, y2, padding=2):
        img_h, img_w = img_ref.shape[:2]
        cv2.rectangle(img_ref, (max(0, int(x1) - padding), max(0, int(y1) - padding)), 
                      (min(img_w, int(x2) + padding), min(img_h, int(y2) + padding)), (0, 0, 0), -1)

    def pixelate_region(img_ref, x1, y1, x2, y2, blocks=12):
        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = min(img_ref.shape[1], int(x2)), min(img_ref.shape[0], int(y2))
        roi = img_ref[y1:y2, x1:x2]
        if roi.size == 0: return
        h, w = roi.shape[:2]
        temp = cv2.resize(roi, (blocks, blocks), interpolation=cv2.INTER_LINEAR)
        img_ref[y1:y2, x1:x2] = cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)

    def line_has_sensitive_pattern(text):
        compact_text = re.sub(r'\s+', '', text)
        digits_only = re.sub(r'\D', '', text)
        if user_choices['id_num']:
            if re.fullmatch(r'[\d\s.-]{8,15}', text.strip()) and 8 <= len(digits_only) <= 12: return True
            if re.search(r'(?:\d[\s.-]?){12}', text) or re.search(r'(?:\d[\s.-]?){9}', text): return True
            if re.search(r'[a-zA-Z]{2}\d{10}', compact_text) or re.search(r'[A-Z]\d{7,8}', compact_text): return True
            if re.search(r'\d{10,13}', compact_text): return True
            if len(digits_only) in [9, 12]: return True
        if user_choices['dob']:
            norm_text = normalize_text(text)
            has_dob_label = any(k in norm_text for k in [
                'ngay sinh',
                'sinh ngay',
                'date of birth',
                'dob'
            ])

            if has_dob_label and (
                re.search(r'\d{2}[\/\-.]\d{2}[\/\-.]\d{4}', text)
                or re.search(r'\d{4}[\/\-.]\d{2}[\/\-.]\d{2}', text)
            ):
                return True
        return False

    def redact_cv_portrait_area(img_ref):
        img_h, img_w = img_ref.shape[:2]
        pixelate_region(img_ref, int(img_w * 0.07), int(img_h * 0.10), int(img_w * 0.36), int(img_h * 0.33), blocks=12)

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

    def redact_cv_contact_smart(img_ref, ocr_items, line_items):
        img_h, img_w = img_ref.shape[:2]
        left_col_limit = int(img_w * 0.45)
        email_pattern_cv = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z0-9]{2,}(?:\.[a-zA-Z0-9]{2,})*'
        phone_pattern_cv = r'''(?<!\d)(?:(?:\+?84|0)[\s.-]?(?:\d[\s.-]?){8,10}|\d{3}[\s.-]?\d{3}[\s.-]?\d{4})(?!\d)'''

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
            redact_rect(img_ref, max(0, x1 - 3), max(0, y1 - 7), min(img_w, x2 + 3), min(img_h, y2 + 4), padding=0)

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
            for match in re.finditer(email_pattern_cv, compact_text):
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
            for match in re.finditer(phone_pattern_cv, compact_text, re.VERBOSE):
                m_start, m_end = match.span()
                matched_items = [p['item'] for p in parts if p['end'] > m_start and p['start'] < m_end]
                if not matched_items: continue
                x1 = min(i['x1'] for i in matched_items)
                y1 = min(i['y1'] for i in matched_items)
                x2 = max(i['x2'] for i in matched_items)
                y2 = max(i['y2'] for i in matched_items)
                redact_rect(img_ref, x1, y1, x2, y2, padding=3)
                found = True
            return found

        for item in ocr_items:
            if not is_left_cv_item(item): continue
            text = item['text'].strip()
            if not text: continue
            if re.search(email_pattern_cv, re.sub(r'\s+', '', text)): redact_email_rect(item['x1'], item['y1'], item['x2'], item['y2'])
            if re.search(phone_pattern_cv, text, re.VERBOSE): redact_rect(img_ref, item['x1'], item['y1'], item['x2'], item['y2'], padding=3)

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

            roi = img_ref[y_start:y_end, x_start:x_end]
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
                x, y, w_box, h_box = cv2.boundingRect(cnt)
                if w_box < 12 or h_box < 3: continue
                if h_box > (y_end - y_start) * 0.8: continue
                boxes.append((x_start + x, y_start + y, x_start + x + w_box, y_start + y + h_box))

            for x1, y1, x2, y2 in merge_boxes_local(boxes, distance_x=10, distance_y=6):
                redact_email_rect(x1, y1, x2, y2)
    def redact_license_plates(img_ref, ocr_items):
        plate_patterns = [
            r'\d{2}[A-Z]{1,2}\d?[-.]?\d{3,5}[.]?\d{0,2}',
            r'\d{2}[-.]?[A-Z]{1,2}\d?[-.]?\d{3,5}[.]?\d{0,2}',
        ]

        items = sorted(ocr_items, key=lambda i: (i['y1'], i['x1']))

        for i in range(len(items)):
            group = items[i:i+4]

            text = ''.join(item['text'].upper() for item in group)
            compact = re.sub(r'[^A-Z0-9]', '', text)

            # Bien so thuong co 2 so dau + chu cai + it nhat 4 so
            looks_like_plate = (
                re.search(r'\d{2}[A-Z]{1,2}\d?', compact)
                and len(re.findall(r'\d', compact)) >= 6
                and len(compact) <= 12
            )

            if looks_like_plate or any(re.search(p, compact) for p in plate_patterns):
                x1 = min(item['x1'] for item in group)
                y1 = min(item['y1'] for item in group)
                x2 = max(item['x2'] for item in group)
                y2 = max(item['y2'] for item in group)

                redact_rect(
                    img_ref,
                    x1 - 8,
                    y1 - 8,
                    x2 + 8,
                    y2 + 8,
                    padding=0
                )
    # ==========================================
    # 6. SỬ DỤNG OCR ĐỂ GOM DÒNG VÀ VẼ CHE
    # ==========================================
    ocr_items = []
    for bbox, easy_text, conf in pre_results:
        xs, ys = [p[0] for p in bbox], [p[1] for p in bbox]
        x1, y1 = int(min(xs) / scale_factor), int(min(ys) / scale_factor)
        x2, y2 = int(max(xs) / scale_factor), int(max(ys) / scale_factor)
        
        easy_text_clean = easy_text.strip()
        if not easy_text_clean: continue
        
        if '<<' in easy_text_clean or easy_text_clean.isdigit() or (conf > 0.85 and easy_text_clean.isupper()):
            final_text = easy_text_clean
        else:
            px1, py1 = max(0, x1 - 2), max(0, y1 - 2)
            px2, py2 = min(img_w, x2 + 2), min(img_h, y2 + 2)
            crop_img = img[py1:py2, px1:px2]
            if crop_img.shape[0] > 5 and crop_img.shape[1] > 5:
                pil_img = Image.fromarray(cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB))
                vietocr_text = vietocr_reader.predict(pil_img).strip()
                words = vietocr_text.split()
                final_text = easy_text_clean if (len(words) > 3 and len(set(words)) < len(words) / 2) else (vietocr_text or easy_text_clean)
            else:
                final_text = easy_text_clean

        ocr_items.append({
            'text': final_text, 'norm_text': normalize_text(final_text), 'conf': conf,
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'center_y': (y1 + y2) // 2, 'height': y2 - y1,
        })

    ocr_items = sorted(ocr_items, key=lambda item: (item['y1'], item['x1']))

    lines = []
    for item in ocr_items:
        added = False
        for line in lines:
            if abs(item['center_y'] - line['center_y']) < max(18, max(12, item['height']) * 0.7):
                line['items'].append(item)
                line['center_y'] = sum([i['center_y'] for i in line['items']]) // len(line['items'])
                added = True
                break
        if not added: lines.append({'center_y': item['center_y'], 'items': [item]})

    line_items = []
    for line in lines:
        items = sorted(line['items'], key=lambda item: item['x1'])
        line_text = ' '.join(item['text'] for item in items)
        line_items.append({
            'text': line_text, 'norm_text': normalize_text(line_text),
            'x1': min(i['x1'] for i in items), 'y1': min(i['y1'] for i in items),
            'x2': max(i['x2'] for i in items), 'y2': max(i['y2'] for i in items),
            'center_y': line['center_y'], 'height': max(i['y2'] for i in items) - min(i['y1'] for i in items),
            'items': items,
        })

    line_items = sorted(line_items, key=lambda item: item['y1'])
    
    redact_boxes = []
    date_pattern = r'\d{1,2}[\/\-.\s]+\d{1,2}[\/\-.\s]+\d{2,4}'
    stop_labels = [
    'ngay sinh', 'sinh ngay', 'date of birth', 'dob', 'nam sinh',
    'nganh', 'khoa hoc', 'khoa',
    'que quan', 'place of origin',
    'noi thuong tru', 'thuong tru', 'place of residence',
    'dia chi', 'address',
    'gioi tinh', 'sex', 'quoc tich', 'nationality',
    'ho ten', 'ho va ten', 'name'
]
    
    def next_line_is_another_label(line):
        return any(label in line['norm_text'] for label in stop_labels)

    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    phone_pattern = r'(0|84|\+84)[3|5|7|8|9][0-9]{8}\b'
    address_start_y = None
    # if not user_choices['address']:
    #     address_anchor_keywords = [
    #         'que quan',
    #         'place of origin',
    #         'noi thuong tru',
    #         'thuong tru',
    #         'place of residence',
    #         'dia chi',
    #         'address'
    #     ]
    #     for line in line_items:
    #         if any(keyword in line['norm_text'] for keyword in address_anchor_keywords):
    #             address_start_y = line['y1']
    #             break

    for index, line in enumerate(line_items):
        is_sensitive = False
        norm = line['norm_text']
        text = line['text']
        address_labels = ['que quan',
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
        if any(kw in norm for kw in ['het han', 'nganh', 'khoa hoc', 'nien khoa', 'truong dai hoc', 'the sinh vien']): continue 

        if not user_choices['dob']:
            if any(kw in norm for kw in ['ngay sinh', 'sinh ngay', 'date of birth', 'dob', 'nam sinh']) or re.search(date_pattern, text): continue

        # --- CHE MRZ TÁCH BIỆT ---
        if '<<' in text:
            has_digits = any(char.isdigit() for char in text)
            if user_choices['name'] and not has_digits:
                redact_boxes.append((line['x1'], line['y1'], line['x2'], line['y2']))
                continue
            if (user_choices['id_num'] or user_choices['dob']) and has_digits:
                redact_boxes.append((line['x1'], line['y1'], line['x2'], line['y2']))
                continue
            continue 

        if any(safe in norm for safe in ['cong hoa xa hoi', 'chu nghia viet nam', 'doc lap tu do', 'hanh phuc', 'can cuoc cong dan', 'citizen identity card', 'giam doc cong an']) and not line_has_sensitive_pattern(text): continue

        if user_choices['dob'] and any(kw in norm for kw in ['ngay sinh', 'sinh ngay', 'date of birth', 'dob', 'nam sinh']):
            matches = list(re.finditer(date_pattern, text))
            if matches:
                for match in matches:
                    start_char, end_char = match.span()
                    char_width = (line['x2'] - line['x1']) / max(1, len(text))
                    redact_rect(img, int(line['x1'] + (start_char * char_width)) - 80, line['y1'], int(line['x1'] + (end_char * char_width)) + 85, line['y2'])
            else:
                if has_keyword(norm, next_line_keywords):
                    for j in range(index + 1, min(index + 2, len(line_items))):
                        next_line = line_items[j]

                        # Nếu dòng kế tiếp là nhãn khác như Giới tính, Quốc tịch, Quê quán,
                        # thì dừng, không che lan xuống địa chỉ.
                        if any(label in next_line['norm_text'] for label in stop_labels):
                            break

                        # Chỉ che dòng kế tiếp nếu dòng đó thật sự có dạng ngày.
                        if re.search(date_pattern, next_line['text']):
                            redact_boxes.append((
                                next_line['x1'], next_line['y1'],
                                next_line['x2'], next_line['y2']
                            ))
            continue 

        if user_choices['name'] and any(kw in norm for kw in ['ho va ten', 'ho ten', 'full name', 'name']):
            match = re.search(r'(ho va ten|ho ten|full name|name)\s*:?', norm)
            if match:
                start_char = match.end()
                if start_char < max(1, len(norm)) - 1:
                    sub_x1 = int(line['x1'] + (start_char * ((line['x2'] - line['x1']) / max(1, len(norm)))))
                    redact_rect(img, sub_x1, line['y1'], line['x2'], line['y2'])
            for j in range(index + 1, min(index + 2, len(line_items))):  
                if any(label in line_items[j]['norm_text'] for label in stop_labels) or (not user_choices['dob'] and re.search(date_pattern, line_items[j]['text'])): break
                redact_boxes.append((line_items[j]['x1'], line_items[j]['y1'], line_items[j]['x2'], line_items[j]['y2']))
            continue

        # --- CHE TỰ DO SĐT / EMAIL VÀ CÁC THÔNG TIN KHÁC ---
        if user_choices['cv_contact']:
            if re.search(email_pattern, text) or re.search(phone_pattern, text):
                is_sensitive = True

        if user_choices['id_num']:
            digits_only = re.sub(r'\D', '', text)
            if len(digits_only) in [12, 16] and len(text) <= 20:
                 is_sensitive = True

        if line_has_sensitive_pattern(text) or has_keyword(norm, sensitive_keywords) or (has_keyword(norm, vietnam_address_words) and len(norm) >= 8): 
            is_sensitive = True

        if has_keyword(norm, multi_line_keywords):
            for j in range(index + 1, min(index + 5, len(line_items))):
                if any(label in line_items[j]['norm_text'] for label in stop_labels) or (not user_choices['dob'] and re.search(date_pattern, line_items[j]['text'])): break
                redact_boxes.append((line_items[j]['x1'], line_items[j]['y1'], line_items[j]['x2'], line_items[j]['y2']))

        if has_keyword(norm, next_line_keywords):
            for j in range(index + 1, min(index + 2, len(line_items))):
                next_norm = line_items[j]['norm_text']

                if not user_choices.get('address') and any(k in next_norm for k in address_labels):
                    continue

                if not next_line_is_another_label(line_items[j]):
                    redact_boxes.append((
                        line_items[j]['x1'],
                        line_items[j]['y1'],
                        line_items[j]['x2'],
                        line_items[j]['y2']
                    ))

        if is_sensitive: redact_boxes.append((line['x1'], line['y1'], line['x2'], line['y2']))

    for x1, y1, x2, y2 in redact_boxes:
        redact_rect(img, max(0, x1 - 5), max(0, y1 - 3), min(img_w, x2 + 5), min(img_h, y2 + 3), padding=0)

    # ==========================================
    # 7. LỚP MỜ HÌNH ẢNH (ẢNH CHÂN DUNG, VÂN TAY, MÃ VẠCH)
    # ==========================================
    if user_choices['qr']:
        for line in line_items:
            if any(anchor in line['norm_text'] for anchor in ['can cuoc cong dan', 'citizen identity card', 'can cuoc']):
                h_text = line['y2'] - line['y1']
                qr_x1, qr_y1, qr_size = line['x2'] + int(h_text * 0.3), line['y1'] - int(h_text * 2.0), int(h_text * 3.0) 
                pixelate_region(img, qr_x1, qr_y1, min(img_w, qr_x1 + qr_size), min(img_h, qr_y1 + qr_size), blocks=12)
                break 

    if user_choices['finger']:
        left_anchors = ['ngon tro trai', 'left index', 'tro trai']
        right_anchors = ['ngon tro phai', 'right index', 'tro phai']
        left_finger_boxes, right_finger_boxes = [], []
        
        for item in ocr_items:
            norm = item['norm_text']
            x1, y1, x2, y2 = item['x1'], item['y1'], item['x2'], item['y2']
            h_text = y2 - y1
            box_data = {
                'x1': max(0, x1 - int(h_text * 1.5)), 'y1': max(0, y1 - int(h_text * 9.0)),
                'x2': min(img_w, x2 + int(h_text * 1.5)), 'y2': max(0, y1 - 2)
            }
            if any(a in norm for a in left_anchors): left_finger_boxes.append(box_data)
            elif any(a in norm for a in right_anchors): right_finger_boxes.append(box_data)

        for right in right_finger_boxes: pixelate_region(img, right['x1'], right['y1'], right['x2'], right['y2'], blocks=8)
        for left in left_finger_boxes: pixelate_region(img, left['x1'], left['y1'], left['x2'], left['y2'], blocks=8)

    if user_choices['face']: 
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        for (x, y, w_face, h_face) in face_cascade.detectMultiScale(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)):
            pixelate_region(img, x, y, x + w_face, y + h_face, blocks=8)
            
        if document_type.startswith("CV"):
            redact_cv_portrait_area(img)
        elif document_type in ["Căn cước công dân (Mặt trước)", "Thẻ sinh viên / Thẻ học sinh"]:
            pixelate_region(img, int(img_w * 0.03), int(img_h * 0.4), int(img_w * 0.30), int(img_h * 0.82), blocks=10)

    if user_choices['cv_contact']:
        redact_cv_contact_smart(img, ocr_items, line_items)
        
    if user_choices.get('plate'):
        redact_license_plates(img, ocr_items)

    if user_choices['barcode']:
        try:
            x1 = int(img_w * 0.35)
            y1 = int(img_h * 0.83)
            x2 = int(img_w * 0.92)
            y2 = int(img_h * 0.98)
            pixelate_region(img, x1, y1, x2, y2, blocks=10)
        except Exception as e:
            print(f"Lỗi khi che mã vạch (đã bỏ qua): {e}")
            
    # --- 8. LƯU ẢNH HỖ TRỢ ĐƯỜNG DẪN TIẾNG VIỆT ---
    try:
        # 1. Ép hệ thống mở khóa bộ nhớ ảnh để OpenCV có thể vẽ mực đen đè lên
        img = np.ascontiguousarray(img, dtype=np.uint8)
        
        # 2. Dùng imencode thay vì imwrite để chống lỗi đường dẫn chứa Tiếng Việt
        is_success, buffer = cv2.imencode(".jpg", img)
        if is_success:
            # 3. Chuyển buffer thành bytes và ghi thẳng vào ổ cứng
            with open(output_path, "wb") as f:
                f.write(buffer.tobytes())
            print(f"✨ Đã lưu ảnh thành công vào: {output_path}")
        else:
            print("Lỗi hệ thống: Không thể mã hóa ảnh.")
            return False
    except Exception as e:
        print(f"Lỗi ghi file: {e}")
        return False
        
    return True