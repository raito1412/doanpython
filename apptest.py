import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image, ImageTk

import cv2
import easyocr
import re
import unicodedata
import numpy as np
import threading


class SensitiveImageMaskingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sensitive Image Masking App")
        self.root.geometry("900x700")
        self.root.configure(bg="#F8EDEB")

        self.original_image = None
        self.masked_image = None
        self.current_photo = None
        self.image_path = None

        self.reader = None

        self.setup_style()
        self.setup_ui()

        # Load EasyOCR sau khi giao diện mở để tránh app bị đơ lúc khởi động
        self.loading_label.config(text="Đang khởi tạo OCR...")
        threading.Thread(target=self.load_ocr_reader, daemon=True).start()

    def load_ocr_reader(self):
        try:
            self.reader = easyocr.Reader(['vi', 'en'], gpu=False)
            self.root.after(0, lambda: self.loading_label.config(text="OCR đã sẵn sàng."))
        except Exception as e:
            self.root.after(
                0,
                lambda: messagebox.showerror("Lỗi OCR", f"Không khởi tạo được EasyOCR:\n{e}")
            )

    def setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Pastel.Horizontal.TProgressbar",
            troughcolor="#FAD2E1",
            background="#A2D2FF",
            bordercolor="#FAD2E1",
            lightcolor="#A2D2FF",
            darkcolor="#A2D2FF"
        )

    def setup_ui(self):
        self.title_label = tk.Label(
            self.root,
            text="Ứng dụng che dữ liệu nhạy cảm trên hình ảnh",
            font=("Arial", 22, "bold"),
            bg="#F8EDEB",
            fg="#4A4E69"
        )
        self.title_label.pack(pady=(25, 5))

        self.description_label = tk.Label(
            self.root,
            text="Tải ảnh lên → Che dữ liệu nhạy cảm → Tải ảnh đã che về máy",
            font=("Arial", 13),
            bg="#F8EDEB",
            fg="#5D576B"
        )
        self.description_label.pack(pady=(0, 20))

        self.image_frame = tk.Frame(
            self.root,
            bg="#FFFFFF",
            highlightbackground="#CDB4DB",
            highlightthickness=3
        )
        self.image_frame.pack(padx=40, pady=10, fill="both", expand=True)

        self.image_title = tk.Label(
            self.image_frame,
            text="Ảnh gốc",
            font=("Arial", 17, "bold"),
            bg="#FFFFFF",
            fg="#4A4E69"
        )
        self.image_title.pack(pady=15)

        self.image_label = tk.Label(
            self.image_frame,
            text="Chưa có ảnh nào được tải lên",
            font=("Arial", 14),
            bg="#FFF1F3",
            fg="#6D6875",
            width=60,
            height=20
        )
        self.image_label.pack(padx=25, pady=10, fill="both", expand=True)

        self.loading_label = tk.Label(
            self.root,
            text="",
            font=("Arial", 12, "bold"),
            bg="#F8EDEB",
            fg="#4A4E69"
        )
        self.loading_label.pack(pady=(10, 0))

        self.progress = ttk.Progressbar(
            self.root,
            orient="horizontal",
            length=600,
            mode="determinate",
            style="Pastel.Horizontal.TProgressbar"
        )
        self.progress.pack(pady=10)

        self.button_frame = tk.Frame(self.root, bg="#F8EDEB")
        self.button_frame.pack(pady=15)

        self.upload_button = tk.Button(
            self.button_frame,
            text="Tải hình ảnh lên",
            command=self.upload_image,
            font=("Arial", 13, "bold"),
            bg="#CDB4DB",
            fg="#3D2C4A",
            activebackground="#BFA2DB",
            activeforeground="#2D2036",
            relief="flat",
            padx=25,
            pady=12,
            cursor="hand2"
        )
        self.upload_button.grid(row=0, column=0, padx=10)

        self.mask_button = tk.Button(
            self.button_frame,
            text="Che dữ liệu nhạy cảm",
            command=self.start_masking_process,
            font=("Arial", 13, "bold"),
            bg="#A2D2FF",
            fg="#1F3A5F",
            activebackground="#8EC5FC",
            activeforeground="#14263D",
            relief="flat",
            padx=25,
            pady=12,
            cursor="hand2",
            state="disabled"
        )
        self.mask_button.grid(row=0, column=1, padx=10)

        self.download_button = tk.Button(
            self.button_frame,
            text="Tải hình ảnh về",
            command=self.download_image,
            font=("Arial", 13, "bold"),
            bg="#B5EAD7",
            fg="#235347",
            activebackground="#95D5B2",
            activeforeground="#173B32",
            relief="flat",
            padx=25,
            pady=12,
            cursor="hand2",
            state="disabled"
        )
        self.download_button.grid(row=0, column=2, padx=10)

    def upload_image(self):
        file_path = filedialog.askopenfilename(
            title="Chọn hình ảnh",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.webp"),
                ("All files", "*.*")
            ]
        )

        if not file_path:
            return

        self.image_path = file_path
        self.original_image = Image.open(file_path).convert("RGB")
        self.masked_image = None

        self.image_title.config(text="Ảnh gốc")
        self.show_image(self.original_image)

        self.mask_button.config(state="normal")
        self.download_button.config(state="disabled")

        self.progress["value"] = 0
        self.loading_label.config(text="Ảnh đã được tải lên.")

    def start_masking_process(self):
        if self.original_image is None:
            messagebox.showwarning("Cảnh báo", "Vui lòng tải hình ảnh lên trước.")
            return

        if self.reader is None:
            messagebox.showwarning("Cảnh báo", "OCR chưa khởi tạo xong. Vui lòng đợi vài giây.")
            return

        self.upload_button.config(state="disabled")
        self.mask_button.config(state="disabled")
        self.download_button.config(state="disabled")

        self.progress["value"] = 10
        self.loading_label.config(text="Đang OCR và che dữ liệu nhạy cảm...")

        threading.Thread(target=self.run_masking_thread, daemon=True).start()

    def run_masking_thread(self):
        try:
            masked = self.mask_sensitive_info(self.original_image.copy())

            self.root.after(0, lambda: self.finish_masking_process(masked))

        except Exception as e:
            self.root.after(0, lambda: self.handle_masking_error(e))

    def finish_masking_process(self, masked):
        self.masked_image = masked

        self.progress["value"] = 100
        self.image_title.config(text="Ảnh đã che dữ liệu nhạy cảm")
        self.show_image(self.masked_image)

        self.loading_label.config(text="Hoàn tất!")

        self.upload_button.config(state="normal")
        self.mask_button.config(state="normal")
        self.download_button.config(state="normal")

    def handle_masking_error(self, error):
        self.loading_label.config(text="Có lỗi xảy ra.")
        self.upload_button.config(state="normal")
        self.mask_button.config(state="normal")
        self.download_button.config(state="disabled")

        messagebox.showerror("Lỗi", f"Không thể che dữ liệu:\n{error}")

    # =========================
    # OCR + CHE DỮ LIỆU
    # =========================

    def remove_accents(self, text):
        text = unicodedata.normalize('NFD', text)
        text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')
        return text

    def normalize_text(self, text):
        text = self.remove_accents(text)
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def get_rect_from_bbox(self, bbox):
        xs = [point[0] for point in bbox]
        ys = [point[1] for point in bbox]

        x1 = int(min(xs))
        y1 = int(min(ys))
        x2 = int(max(xs))
        y2 = int(max(ys))

        return x1, y1, x2, y2

    def redact_rect(self, img, x1, y1, x2, y2, padding=10):
        img_h, img_w = img.shape[:2]

        x1 = max(0, int(x1) - padding)
        y1 = max(0, int(y1) - padding)
        x2 = min(img_w, int(x2) + padding)
        y2 = min(img_h, int(y2) + padding)

        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), -1)

    def line_has_sensitive_pattern(self, text):
        digits_only = re.sub(r'\D', '', text)

        patterns = [
            r'(?:\d[\s.-]?){12}',                              # CCCD 12 số
            r'(?:\d[\s.-]?){9}',                               # CMND 9 số
            r'\d{2}[\/\-.]\d{2}[\/\-.]\d{4}',                  # ngày 14/05/2006
            r'\d{4}[\/\-.]\d{2}[\/\-.]\d{2}',                  # ngày 2006-05-14
            r'0\d{9,10}',                                      # số điện thoại VN
            r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', # email
            r'\d{10,13}',                                      # mã số thuế / mã định danh
            r'[A-Z]\d{7,8}',                                   # hộ chiếu
            r'\d{2}[A-Z]-\d{3}\.\d{2}',                        # biển số xe
            r'\d{2}[A-Z]\d-\d{3}\.\d{2}',
            r'\d{2}[A-Z][A-Z]-\d{3}\.\d{2}',
        ]

        for pattern in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return True

        if len(digits_only) >= 8:
            return True

        return False

    def mask_sensitive_info(self, pil_image):
        # PIL RGB -> OpenCV BGR
        img_rgb = np.array(pil_image)
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

        results = self.reader.readtext(img_rgb)

        self.root.after(0, lambda: self.progress.config(value=40))

        ocr_items = []

        for bbox, text, conf in results:
            text = text.strip()

            if not text:
                continue

            x1, y1, x2, y2 = self.get_rect_from_bbox(bbox)

            ocr_items.append({
                'text': text,
                'norm_text': self.normalize_text(text),
                'conf': conf,
                'x1': x1,
                'y1': y1,
                'x2': x2,
                'y2': y2,
                'center_y': (y1 + y2) // 2,
                'height': y2 - y1,
            })

        ocr_items = sorted(ocr_items, key=lambda item: (item['y1'], item['x1']))

        lines = []

        for item in ocr_items:
            added = False

            for line in lines:
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
            norm_line_text = self.normalize_text(line_text)

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

        self.root.after(0, lambda: self.progress.config(value=70))

        sensitive_keywords = [
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

            'ho va ten',
            'ho ten',
            'full name',
            'name',

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

            'gioi tinh',
            'sex',
            'gender',
            'quoc tich',
            'nationality',
            'dan toc',
            'religion',
            'ton giao',

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

        redact_boxes = []

        for index, line in enumerate(line_items):
            norm = line['norm_text']
            text = line['text']

            is_sensitive = False

            if self.line_has_sensitive_pattern(text):
                is_sensitive = True

            if any(keyword in norm for keyword in sensitive_keywords):
                is_sensitive = True

            if any(word in norm for word in vietnam_address_words) and len(norm) >= 8:
                is_sensitive = True

            if any(keyword in norm for keyword in multi_line_keywords):
                for j in range(index, min(index + 5, len(line_items))):
                    redact_boxes.append((
                        line_items[j]['x1'],
                        line_items[j]['y1'],
                        line_items[j]['x2'],
                        line_items[j]['y2']
                    ))

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

        # Che thêm OCR item lẻ nếu keyword bị tách
        for item in ocr_items:
            norm = item['norm_text']

            if any(keyword in norm for keyword in sensitive_keywords):
                redact_boxes.append((
                    item['x1'],
                    item['y1'],
                    item['x2'],
                    item['y2']
                ))

        img_h, img_w = img_bgr.shape[:2]

        expanded_boxes = []

        for x1, y1, x2, y2 in redact_boxes:
            expanded_boxes.append((
                max(0, x1 - 18),
                max(0, y1 - 12),
                min(img_w, x2 + 18),
                min(img_h, y2 + 12),
            ))

        for x1, y1, x2, y2 in expanded_boxes:
            self.redact_rect(img_bgr, x1, y1, x2, y2, padding=0)

        # OpenCV BGR -> PIL RGB
        result_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        result_pil = Image.fromarray(result_rgb)

        return result_pil

    def show_image(self, image):
        display_image = self.resize_image_for_display(image)
        self.current_photo = ImageTk.PhotoImage(display_image)

        self.image_label.config(
            image=self.current_photo,
            text="",
            bg="#FFFFFF"
        )

    def resize_image_for_display(self, image):
        max_width = 700
        max_height = 420

        image_copy = image.copy()
        image_copy.thumbnail((max_width, max_height))

        return image_copy

    def download_image(self):
        if self.masked_image is None:
            messagebox.showwarning("Cảnh báo", "Chưa có ảnh đã che để tải về.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Lưu hình ảnh đã che",
            defaultextension=".png",
            filetypes=[
                ("PNG Image", "*.png"),
                ("JPEG Image", "*.jpg"),
                ("All files", "*.*")
            ]
        )

        if not save_path:
            return

        self.masked_image.save(save_path)
        messagebox.showinfo("Thành công", "Ảnh đã được lưu thành công!")


if __name__ == "__main__":
    root = tk.Tk()
    app = SensitiveImageMaskingApp(root)
    root.mainloop()
