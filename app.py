import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw


class SensitiveImageMaskingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sensitive Image Masking App")
        self.root.geometry("900x700")
        self.root.configure(bg="#F8EDEB")

        self.original_image = None
        self.masked_image = None
        self.current_photo = None

        self.setup_style()
        self.setup_ui()

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
            #text="Tải ảnh lên → Che dữ liệu nhạy cảm → Tải ảnh đã che về máy",
            font=("Arial", 13),
            bg="#F8EDEB",
            fg="#5D576B"
        )
        self.description_label.pack(pady=(0, 20))

        # Khu vực hiển thị ảnh
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

        # Loading
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

        # Nút chức năng
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

        self.original_image = Image.open(file_path)
        self.masked_image = None

        self.image_title.config(text="Ảnh gốc")
        self.show_image(self.original_image)

        self.mask_button.config(state="normal")
        self.download_button.config(state="disabled")

        self.progress["value"] = 0
        self.loading_label.config(text="")

    def start_masking_process(self):
        if self.original_image is None:
            messagebox.showwarning("Cảnh báo", "Vui lòng tải hình ảnh lên trước.")
            return

        self.upload_button.config(state="disabled")
        self.mask_button.config(state="disabled")
        self.download_button.config(state="disabled")

        self.progress["value"] = 0
        self.loading_label.config(text="Đang che dữ liệu nhạy cảm...")

        self.simulate_loading()

    def simulate_loading(self):
        value = self.progress["value"]

        if value < 100:
            self.progress["value"] = value + 5
            self.root.after(100, self.simulate_loading)
        else:
            self.finish_masking_process()

    def finish_masking_process(self):
        # Demo giao diện: giả lập việc che dữ liệu nhạy cảm
        self.masked_image = self.create_demo_masked_image(self.original_image.copy())

        # Sau khi xử lý xong, đổi từ khung ảnh gốc sang khung ảnh đã che
        self.image_title.config(text="Ảnh đã che dữ liệu nhạy cảm")
        self.show_image(self.masked_image)

        self.loading_label.config(text="Hoàn tất!")

        self.upload_button.config(state="normal")
        self.mask_button.config(state="normal")
        self.download_button.config(state="normal")

    def create_demo_masked_image(self, image):
        """
        Đây chỉ là demo giao diện.
        Chưa có logic nhận diện dữ liệu nhạy cảm thật.
        Sau này sẽ thay bằng OCR + Presidio + OpenCV.
        """

        draw = ImageDraw.Draw(image)
        width, height = image.size

        # Các vùng che giả lập
        boxes = [
            (
                int(width * 0.10),
                int(height * 0.12),
                int(width * 0.60),
                int(height * 0.20)
            ),
            (
                int(width * 0.15),
                int(height * 0.35),
                int(width * 0.75),
                int(height * 0.43)
            ),
            (
                int(width * 0.20),
                int(height * 0.60),
                int(width * 0.85),
                int(height * 0.68)
            ),
        ]

        for box in boxes:
            draw.rounded_rectangle(
                box,
                radius=12,
                fill="#FFAFCC"
            )

        return image

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