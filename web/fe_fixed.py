import os
import re
import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

from PIL import Image, ImageTk


DB_NAME = "social_app.db"


# ================= DATABASE SYSTEM =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            phone TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            avatar_path TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS friends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_phone TEXT NOT NULL,
            friend_phone TEXT NOT NULL,
            UNIQUE(user_phone, friend_phone)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_phone TEXT NOT NULL,
            author_name TEXT NOT NULL,
            content TEXT,
            image_path TEXT,
            mask_enabled INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            timestamp TEXT,
            FOREIGN KEY(author_phone) REFERENCES users(phone)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            author_phone TEXT,
            author_name TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT,
            FOREIGN KEY(post_id) REFERENCES posts(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_phone TEXT NOT NULL,
            receiver_phone TEXT NOT NULL,
            content TEXT,
            image_path TEXT,
            mask_enabled INTEGER DEFAULT 0,
            timestamp TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS remember_me (
            id INTEGER PRIMARY KEY,
            phone TEXT,
            password TEXT
        )
    """)

    # Fix database cũ: thêm cột nếu thiếu, không làm mất dữ liệu cũ.
    safe_add_column(cursor, "users", "avatar_path", "TEXT")
    safe_add_column(cursor, "comments", "author_phone", "TEXT")
    safe_add_column(cursor, "comments", "timestamp", "TEXT")

    sample_users = [
        ("0911223344", "12345678", "Nguyễn Văn A", ""),
        ("0988776655", "12345678", "Trần Thị B", ""),
        ("0900112233", "12345678", "Lê Hoàng C", ""),
    ]

    for user in sample_users:
        cursor.execute("SELECT phone FROM users WHERE phone=?", (user[0],))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (phone, password, name, avatar_path) VALUES (?, ?, ?, ?)",
                user,
            )

    conn.commit()
    conn.close()


def safe_add_column(cursor, table_name, column_name, column_type):
    try:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
    except sqlite3.OperationalError:
        pass


# ================= APPLICATION CLASS =================
class SocialChatApp:
    def safe_open_chat(self, partner_phone, partner_name):
        """Hàm an toàn để mở chat"""
        if not hasattr(self, 'chat_panel') or self.chat_panel is None:
            messagebox.showwarning("Chưa sẵn sàng", "Vui lòng chờ giao diện load xong!")
            return
        
        try:
            # Xóa nội dung cũ
            for child in self.chat_panel.winfo_children():
                child.destroy()

            # Tạo chat component
            ChatWindowComponent(
                parent=self.chat_panel,
                my_phone=self.current_user_phone,
                partner_phone=partner_phone,
                partner_name=partner_name,
                image_store=self.chat_images,
                avatar_refs=self.avatar_refs,
                embedded=True,
            )
        except Exception as e:
            messagebox.showerror("Lỗi chat", f"Không thể mở cuộc trò chuyện:\n{str(e)}")
    def edit_post(self, post_id, old_content):
        new_content = simpledialog.askstring(
            "Sửa bài viết",
            "Nhập nội dung mới:",
            initialvalue=old_content,
            parent=self.root,
        )
        if new_content is None:
            return
        new_content = new_content.strip()
        if not new_content:
            messagebox.showwarning("Thiếu nội dung", "Nội dung bài viết không được để trống!")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE posts SET content = ?, timestamp = ? WHERE id = ?",
            (new_content, datetime.now().strftime("%Y-%m-%d %H:%M"), post_id),
        )
        conn.commit()
        conn.close()
        self.load_feed_from_db()

    def delete_post(self, post_id):
        confirm = messagebox.askyesno(
            "Xóa bài viết",
            "Bạn có chắc chắn muốn xóa bài viết này?\nCác bình luận liên quan cũng sẽ bị xóa.",
        )
        if not confirm:
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Xóa comment trước
        cursor.execute("DELETE FROM comments WHERE post_id = ?", (post_id,))
        # Xóa bài viết
        cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
        conn.close()
        self.load_feed_from_db()

    def __init__(self, root):
        self.root = root
        self.root.title("Social Network Demo")
        self.root.geometry("980x750")
        self.root.minsize(850, 650)
        self.root.configure(bg="#E8F1F5")

        self.current_user_phone = None
        self.current_user_name = None
        self.current_user_avatar = ""

        self.feed_images = {}
        self.chat_images = []
        self.avatar_refs = {}
        self.current_chat_component = None
        self.show_login_screen()

    def clear_root(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    # ================= 1. SCREEN: LOGIN & REGISTER =================
    def show_login_screen(self):
        self.clear_root()

        login_frame = tk.Frame(
            self.root,
            bg="#F0F7F4",
            padx=35,
            pady=35,
            bd=1,
            relief="solid",
        )
        login_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            login_frame,
            text="ĐĂNG NHẬP",
            bg="#F0F7F4",
            fg="#2C3E50",
            font=("Arial", 18, "bold"),
        ).pack(pady=(0, 25))

        tk.Label(
            login_frame,
            text="Số điện thoại:",
            bg="#F0F7F4",
            fg="#566573",
            font=("Arial", 10, "bold"),
        ).pack(anchor="w")
        self.ent_phone = tk.Entry(login_frame, font=("Arial", 11), width=32, bg="#FFFFFF", fg="#2C3E50")
        self.ent_phone.pack(pady=(5, 15), ipady=6)

        tk.Label(
            login_frame,
            text="Mật khẩu:",
            bg="#F0F7F4",
            fg="#566573",
            font=("Arial", 10, "bold"),
        ).pack(anchor="w")
        self.ent_pwd = tk.Entry(
            login_frame,
            font=("Arial", 11),
            width=32,
            bg="#FFFFFF",
            fg="#2C3E50",
            show="*",
        )
        self.ent_pwd.pack(pady=(5, 20), ipady=6)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT phone, password FROM remember_me WHERE id=1")
        remembered = cursor.fetchone()
        conn.close()

        if remembered:
            self.ent_phone.insert(0, remembered[0])
            self.ent_pwd.insert(0, remembered[1])

        self.ent_phone.bind("<Return>", lambda event: self.handle_login())
        self.ent_pwd.bind("<Return>", lambda event: self.handle_login())

        tk.Button(
            login_frame,
            text="Đăng nhập",
            command=self.handle_login,
            bg="#A8DADC",
            fg="#1D3557",
            font=("Arial", 11, "bold"),
            bd=0,
            width=30,
            pady=8,
            cursor="hand2",
        ).pack(pady=5)

        tk.Button(
            login_frame,
            text="Tạo tài khoản mới",
            command=self.show_register_screen,
            bg="#F0F7F4",
            fg="#457B9D",
            font=("Arial", 10, "underline"),
            bd=0,
            cursor="hand2",
        ).pack(pady=5)

    def show_register_screen(self):
        self.clear_root()
        self.reg_avatar_path = ""

        reg_frame = tk.Frame(
            self.root,
            bg="#F0F7F4",
            padx=35,
            pady=35,
            bd=1,
            relief="solid",
        )
        reg_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            reg_frame,
            text="ĐĂNG KÝ TÀI KHOẢN",
            bg="#F0F7F4",
            fg="#2C3E50",
            font=("Arial", 16, "bold"),
        ).pack(pady=(0, 25))

        tk.Label(reg_frame, text="Tên hiển thị:", bg="#F0F7F4", fg="#566573", font=("Arial", 10, "bold")).pack(anchor="w")
        self.ent_reg_name = tk.Entry(reg_frame, font=("Arial", 11), width=32, bg="#FFFFFF", fg="#2C3E50")
        self.ent_reg_name.pack(pady=(5, 12), ipady=6)

        tk.Label(reg_frame, text="Số điện thoại Việt Nam:", bg="#F0F7F4", fg="#566573", font=("Arial", 10, "bold")).pack(anchor="w")
        self.ent_reg_phone = tk.Entry(reg_frame, font=("Arial", 11), width=32, bg="#FFFFFF", fg="#2C3E50")
        self.ent_reg_phone.pack(pady=(5, 12), ipady=6)

        tk.Label(reg_frame, text="Mật khẩu (>= 8 ký tự):", bg="#F0F7F4", fg="#566573", font=("Arial", 10, "bold")).pack(anchor="w")
        self.ent_reg_pwd = tk.Entry(reg_frame, font=("Arial", 11), width=32, bg="#FFFFFF", fg="#2C3E50", show="*")
        self.ent_reg_pwd.pack(pady=(5, 20), ipady=6)

        def choose_reg_avatar():
            path = filedialog.askopenfilename(
                title="Chọn ảnh đại diện",
                filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")],
            )
            if path:
                self.reg_avatar_path = path
                lbl_path_status.config(text=os.path.basename(path), fg="#1D3557")

        tk.Button(
            reg_frame,
            text="Tải lên ảnh đại diện (Tùy chọn)",
            command=choose_reg_avatar,
            bg="#E8F1F5",
            fg="#2C3E50",
            font=("Arial", 9),
        ).pack(pady=(0, 2))

        lbl_path_status = tk.Label(
            reg_frame,
            text="Chưa chọn ảnh",
            bg="#F0F7F4",
            fg="#9CA3AF",
            font=("Arial", 8, "italic"),
        )
        lbl_path_status.pack(pady=(0, 15))

        self.ent_reg_name.bind("<Return>", lambda event: self.handle_register())
        self.ent_reg_phone.bind("<Return>", lambda event: self.handle_register())
        self.ent_reg_pwd.bind("<Return>", lambda event: self.handle_register())

        tk.Button(
            reg_frame,
            text="Đăng ký",
            command=self.handle_register,
            bg="#A8E6CF",
            fg="#1D3557",
            font=("Arial", 11, "bold"),
            bd=0,
            width=30,
            pady=8,
            cursor="hand2",
        ).pack(pady=5)

        tk.Button(
            reg_frame,
            text="Quay lại đăng nhập",
            command=self.show_login_screen,
            bg="#F0F7F4",
            fg="#566573",
            font=("Arial", 10),
            bd=0,
            cursor="hand2",
        ).pack(pady=5)

    def validate_user_inputs(self, phone, pwd):
        phone_regex = r"^(03|05|07|08|09)\d{8}$"
        if not re.match(phone_regex, phone):
            messagebox.showerror(
                "Lỗi dữ liệu",
                "Số điện thoại không hợp lệ! Vui lòng nhập số điện thoại Việt Nam gồm 10 chữ số.",
            )
            return False
        if len(pwd) < 8:
            messagebox.showerror("Lỗi dữ liệu", "Mật khẩu phải từ 8 ký tự trở lên!")
            return False
        return True

    def handle_login(self):
        phone = self.ent_phone.get().strip()
        pwd = self.ent_pwd.get().strip()

        if not self.validate_user_inputs(phone, pwd):
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT phone, password, name, avatar_path FROM users WHERE phone=? AND password=?", (phone, pwd))
        user = cursor.fetchone()

        if not user:
            conn.close()
            messagebox.showerror("Thất bại", "Số điện thoại hoặc mật khẩu chưa chính xác!")
            return

        cursor.execute("DELETE FROM remember_me")
        cursor.execute("INSERT INTO remember_me (id, phone, password) VALUES (1, ?, ?)", (phone, pwd))
        conn.commit()
        conn.close()

        self.current_user_phone = user[0]
        self.current_user_name = user[2]
        self.current_user_avatar = user[3] or ""
        self.build_main_ui()

    def handle_register(self):
        name = self.ent_reg_name.get().strip()
        phone = self.ent_reg_phone.get().strip()
        pwd = self.ent_reg_pwd.get().strip()

        if not name:
            messagebox.showerror("Lỗi", "Vui lòng điền tên hiển thị!")
            return
        if not self.validate_user_inputs(phone, pwd):
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT phone FROM users WHERE phone=?", (phone,))
        if cursor.fetchone():
            conn.close()
            messagebox.showerror("Lỗi", "Số điện thoại này đã tồn tại trên hệ thống!")
            return

        try:
            cursor.execute(
                "INSERT INTO users (phone, password, name, avatar_path) VALUES (?, ?, ?, ?)",
                (phone, pwd, name, self.reg_avatar_path),
            )
            conn.commit()
            messagebox.showinfo("Thành công", "Đăng ký thành công! Hãy đăng nhập hệ thống.")
            self.show_login_screen()
        except sqlite3.Error as exc:
            messagebox.showerror("Lỗi", f"Không thể tạo tài khoản: {exc}")
        finally:
            conn.close()

    def handle_logout_clear(self):
        self.current_user_phone = None
        self.current_user_name = None
        self.current_user_avatar = ""
        self.feed_images.clear()
        self.chat_images.clear()
        self.avatar_refs.clear()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM remember_me")
        conn.commit()
        conn.close()

        self.show_login_screen()
        self.ent_phone.delete(0, "end")
        self.ent_pwd.delete(0, "end")
        self.ent_phone.focus_set()

    # ================= 2. MAIN SOCIAL FEED & SIDEBAR =================
    def build_main_ui(self):
        self.clear_root()
        self.post_image_path = None
        self.post_preview_photo = None
        self.post_mask_var = tk.BooleanVar(value=False)

        # === 1. HEADER (Phần trên cùng) ===
        header = tk.Frame(self.root, bg="#D8E2DC", height=60, bd=1, relief="groove")
        header.pack(fill="x")
        header.pack_propagate(False)

        self.render_avatar(header, self.current_user_name, self.current_user_avatar, "me", bg="#D8E2DC")
        tk.Label(header, text=f" Mạng Xã Hội | {self.current_user_name}", bg="#D8E2DC", fg="#2C3E50", font=("Arial", 13, "bold")).pack(side="left", padx=5, pady=15)
        tk.Button(header, text="Đăng xuất", command=self.handle_logout_clear, bg="#FFADAD", fg="#780000", font=("Arial", 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2").pack(side="right", padx=20, pady=12)

        # === KHU VỰC NỘI DUNG CHÍNH (Chia 3 cột) ===
        main_content = tk.Frame(self.root, bg="#E8F1F5")
        main_content.pack(fill="both", expand=True)

        # CỘT 1: SIDEBAR (Vẽ khung trái trước)
        sidebar = tk.Frame(main_content, bg="#F4F1DE", width=240, bd=1, relief="groove")
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        search_box = tk.LabelFrame(sidebar, text=" Tìm bạn bằng SĐT", bg="#F4F1DE", fg="#2C3E50", font=("Arial", 10, "bold"), padx=10, pady=10)
        search_box.pack(fill="x", padx=12, pady=15)
        self.ent_search_phone = tk.Entry(search_box, font=("Arial", 10), bg="#FFFFFF", fg="#2C3E50")
        self.ent_search_phone.pack(fill="x", ipady=4, pady=(0, 8))
        self.ent_search_phone.bind("<Return>", lambda event: self.handle_add_friend())
        tk.Button(search_box, text="Tìm & Kết bạn", command=self.handle_add_friend, bg="#E9C46A", fg="#1D3557", font=("Arial", 9, "bold"), bd=0, pady=5, cursor="hand2").pack(fill="x")

        tk.Label(sidebar, text=" Bạn bè của bạn:", bg="#F4F1DE", fg="#566573", font=("Arial", 10, "bold")).pack(anchor="w", padx=15, pady=(10, 2))
        self.friend_list_frame = tk.Frame(sidebar, bg="#F4F1DE")
        self.friend_list_frame.pack(fill="both", expand=True, padx=15)
        self.update_sidebar_friends()

        # CỘT 2: CHAT PANEL (Vẽ khung phải ngay sau đó để giữ chỗ)
        self.chat_panel = tk.Frame(main_content, bg="#E8F1F5", width=350, bd=1, relief="groove")
        self.chat_panel.pack(side="right", fill="both", padx=(0, 10), pady=15)
        self.chat_panel.pack_propagate(False)

        self.chat_placeholder_label = tk.Label(
            self.chat_panel,
            text="Chọn một bạn trong danh sách\nbên trái để bắt đầu trò chuyện",
            bg="#E8F1F5",
            fg="#6B7280",
            font=("Arial", 10, "italic"),
            justify="center",
        )
        self.chat_placeholder_label.pack(expand=True)

        # CỘT 3: FEED BẢNG TIN (Vẽ ở giữa cuối cùng để nó chiếm trọn không gian thừa)
        feed_container = tk.Frame(main_content, bg="#E8F1F5")
        feed_container.pack(side="left", fill="both", expand=True, padx=15, pady=15)

        self.feed_canvas = tk.Canvas(feed_container, bg="#E8F1F5", highlightthickness=0)
        self.feed_canvas.pack(side="left", fill="both", expand=True)

        feed_scrollbar = tk.Scrollbar(feed_container, orient="vertical", command=self.feed_canvas.yview)
        feed_scrollbar.pack(side="right", fill="y")
        self.feed_canvas.configure(yscrollcommand=feed_scrollbar.set)

        self.feed_frame = tk.Frame(self.feed_canvas, bg="#E8F1F5")
        self.feed_window = self.feed_canvas.create_window((0, 0), window=self.feed_frame, anchor="nw")
        self.feed_frame.bind("<Configure>", lambda event: self.feed_canvas.configure(scrollregion=self.feed_canvas.bbox("all")))
        self.feed_canvas.bind("<Configure>", lambda event: self.feed_canvas.itemconfig(self.feed_window, width=event.width))

        self.create_post_box()
        self.load_feed_from_db()


    def render_avatar(self, parent, name, avatar_path, key, bg="#FFFFFF"):
        if avatar_path and os.path.exists(avatar_path):
            try:
                img = Image.open(avatar_path).resize((32, 32))
                photo = ImageTk.PhotoImage(img)
                self.avatar_refs[key] = photo
                tk.Label(parent, image=photo, bg=bg).pack(side="left", padx=(10, 0), pady=10)
                return
            except Exception:
                pass

        first_char = name[0].upper() if name else "?"
        tk.Label(
            parent,
            text=first_char,
            bg="#A8DADC",
            fg="#1D3557",
            font=("Arial", 10, "bold"),
            width=3,
            height=1,
        ).pack(side="left", padx=(10, 0), pady=10)

    def handle_add_friend(self):
        target_phone = self.ent_search_phone.get().strip()
        if not target_phone:
            return
        if target_phone == self.current_user_phone:
            messagebox.showwarning("Chú ý", "Bạn không thể tự kết bạn với chính mình!")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM users WHERE phone=?", (target_phone,))
        user_found = cursor.fetchone()

        if not user_found:
            conn.close()
            messagebox.showerror("Không tìm thấy", "Không có người dùng nào sử dụng số điện thoại này!")
            return

        friend_name = user_found[0]
        cursor.execute(
            "SELECT id FROM friends WHERE user_phone=? AND friend_phone=?",
            (self.current_user_phone, target_phone),
        )
        if cursor.fetchone():
            conn.close()
            messagebox.showinfo("Thông báo", f"Bạn và {friend_name} đã là bạn bè từ trước!")
            return

        confirm = messagebox.askyesno(
            "Xác nhận kết bạn",
            f"Hệ thống tìm thấy người dùng:\nTên: {friend_name}\nSĐT: {target_phone}\n\nBạn có muốn kết bạn với người này không?",
        )
        if confirm:
            cursor.execute(
                "INSERT OR IGNORE INTO friends (user_phone, friend_phone) VALUES (?, ?)",
                (self.current_user_phone, target_phone),
            )
            cursor.execute(
                "INSERT OR IGNORE INTO friends (user_phone, friend_phone) VALUES (?, ?)",
                (target_phone, self.current_user_phone),
            )
            conn.commit()
            messagebox.showinfo("Thành công", f"Đã kết bạn thành công với {friend_name}!")
            self.ent_search_phone.delete(0, "end")
            self.update_sidebar_friends()
        conn.close()

    def update_sidebar_friends(self):
        for child in self.friend_list_frame.winfo_children():
            child.destroy()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT users.name, users.phone
            FROM friends
            JOIN users ON friends.friend_phone = users.phone
            WHERE friends.user_phone = ?
            ORDER BY users.name
            """,
            (self.current_user_phone,),
        )
        friend_rows = cursor.fetchall()
        conn.close()

        if not friend_rows:
            tk.Label(
                self.friend_list_frame,
                text="(Chưa có bạn bè,\nhãy tìm kiếm ở trên)",
                bg="#F4F1DE",
                fg="#9CA3AF",
                font=("Arial", 9, "italic"),
            ).pack(anchor="w", pady=5)
            return

        for name, phone in friend_rows:
            btn = tk.Button(
                self.friend_list_frame,
                text=f"• {name}",
                bg="#F4F1DE",
                fg="#2C3E50",
                activebackground="#E8F1F5",
                font=("Arial", 10),
                anchor="w",
                bd=0,
                cursor="hand2",
                width=20,
            )
            # Dùng lambda an toàn
            btn.configure(command=lambda p=phone, n=name: self.safe_open_chat(p, n))
            btn.pack(fill="x", pady=2)


    def create_post_box(self):
        box = tk.Frame(self.feed_frame, bg="#F0F7F4", padx=16, pady=14, bd=1, relief="solid")
        box.pack(fill="x", pady=(0, 16))

        tk.Label(box, text="✍️ Đăng bài viết mới", bg="#F0F7F4", fg="#2C3E50", font=("Arial", 11, "bold")).pack(anchor="w")

        self.post_text = tk.Text(
            box,
            height=3,
            font=("Arial", 11),
            bg="#FFFFFF",
            fg="#2C3E50",
            bd=1,
            relief="solid",
            padx=10,
            pady=8,
            wrap="word",
        )
        self.post_text.pack(fill="x", pady=10)

        self.post_preview_frame = tk.Frame(box, bg="#FFFFFF")
        self.post_preview_frame.pack_forget()
        self.post_preview_label = tk.Label(self.post_preview_frame, bg="#FFFFFF")
        self.post_preview_label.pack(side="left", padx=5, pady=5)
        self.post_file_label = tk.Label(self.post_preview_frame, text="", bg="#FFFFFF", fg="#2C3E50", font=("Arial", 9))
        self.post_file_label.pack(side="left", padx=5)
        tk.Button(
            self.post_preview_frame,
            text="✕",
            command=self.remove_post_image,
            bg="#FFADAD",
            fg="#780000",
            bd=0,
            padx=5,
            cursor="hand2",
        ).pack(side="right", padx=5)

        action_row = tk.Frame(box, bg="#F0F7F4")
        action_row.pack(fill="x")

        tk.Button(
            action_row,
            text="Thêm ảnh",
            command=self.choose_post_image,
            bg="#E8F1F5",
            fg="#2C3E50",
            font=("Arial", 10),
            bd=1,
            relief="groove",
            padx=10,
            pady=5,
            cursor="hand2",
        ).pack(side="left")

        tk.Checkbutton(
            action_row,
            text="Che dữ liệu",
            variable=self.post_mask_var,
            bg="#F0F7F4",
            fg="#2C3E50",
            font=("Arial", 10),
        ).pack(side="left", padx=10)

        tk.Button(
            action_row,
            text="Đăng bài",
            command=self.publish_post,
            bg="#A8DADC",
            fg="#1D3557",
            font=("Arial", 10, "bold"),
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
        ).pack(side="right")

    def choose_post_image(self):
        file_path = filedialog.askopenfilename(
            title="Chọn hình ảnh",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")],
        )
        if not file_path:
            return

        self.post_image_path = file_path
        img = Image.open(file_path)
        img.thumbnail((80, 80))
        self.post_preview_photo = ImageTk.PhotoImage(img)
        self.post_preview_label.config(image=self.post_preview_photo)
        self.post_file_label.config(text=os.path.basename(file_path))
        self.post_preview_frame.pack(fill="x", pady=5)

    def remove_post_image(self):
        self.post_image_path = None
        self.post_preview_photo = None
        self.post_preview_label.config(image="")
        self.post_file_label.config(text="")
        self.post_preview_frame.pack_forget()

    def publish_post(self):
        content = self.post_text.get("1.0", "end").strip()
        if not content and not self.post_image_path:
            return

        mask_val = 1 if self.post_mask_var.get() else 0
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO posts (author_phone, author_name, content, image_path, mask_enabled, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (self.current_user_phone, self.current_user_name, content, self.post_image_path, mask_val, now_str),
        )
        conn.commit()
        conn.close()

        self.post_text.delete("1.0", "end")
        self.remove_post_image()
        self.post_mask_var.set(False)
        self.load_feed_from_db()

    def load_feed_from_db(self):
        # Giữ lại ô đăng bài ở vị trí đầu tiên, chỉ xóa danh sách bài cũ phía dưới.
        children = self.feed_frame.winfo_children()
        for child in children[1:]:
            child.destroy()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # CHỈ lấy bài:
        # - của chính mình
        # - của những người là bạn bè với mình
        cursor.execute(
            """
            SELECT p.id, p.author_phone, p.author_name, p.content,
                   p.image_path, p.mask_enabled, p.likes, p.timestamp,
                   u.avatar_path
            FROM posts AS p
            LEFT JOIN users AS u ON p.author_phone = u.phone
            WHERE 
                p.author_phone = ?
                OR p.author_phone IN (
                    SELECT friend_phone 
                    FROM friends 
                    WHERE user_phone = ?
                )
            ORDER BY p.id DESC
            """,
            (self.current_user_phone, self.current_user_phone),
        )
        posts = cursor.fetchall()
        conn.close()

        for post in posts:
            self.render_post_item(*post)


    def render_post_item(self, post_id, author_phone, author, content, img_path, mask_enabled, likes, time_str, author_avatar):
        p_frame = tk.Frame(self.feed_frame, bg="#FFFFFF", padx=14, pady=12, bd=1, relief="solid")
        p_frame.pack(fill="x", pady=(0, 12))

        top = tk.Frame(p_frame, bg="#FFFFFF")
        top.pack(fill="x")
        self.render_avatar(top, author, author_avatar, f"post_{post_id}", bg="#FFFFFF")

        info_f = tk.Frame(top, bg="#FFFFFF")
        info_f.pack(side="left", padx=8)
        tk.Label(info_f, text=author, bg="#FFFFFF", fg="#2C3E50", font=("Arial", 11, "bold")).pack(anchor="w")
        tk.Label(info_f, text=time_str or "", bg="#FFFFFF", fg="#6B7280", font=("Arial", 8)).pack(anchor="w")

        if content:
            tk.Label(
                p_frame,
                text=content,
                bg="#FFFFFF",
                fg="#2C3E50",
                font=("Arial", 11),
                justify="left",
                wraplength=600,
            ).pack(anchor="w", pady=8)

        if img_path and os.path.exists(img_path):
            try:
                img = Image.open(img_path)
                img.thumbnail((450, 300))
                photo = ImageTk.PhotoImage(img)
                self.feed_images[f"p_{post_id}"] = photo
                tk.Label(p_frame, image=photo, bg="#FFFFFF").pack(anchor="w", pady=5)
            except Exception:
                pass

        if mask_enabled:
            tk.Label(
                p_frame,
                text="Bài viết được ẩn thông tin nhạy cảm",
                bg="#F4F1DE",
                fg="#D97706",
                font=("Arial", 9, "italic"),
            ).pack(anchor="w", pady=4)

        stats_frame = tk.Frame(p_frame, bg="#FFFFFF")
        stats_frame.pack(fill="x", pady=4)
        tk.Label(
            stats_frame,
            text=f"❤️ {likes} lượt thích",
            bg="#FFFFFF",
            fg="#457B9D",
            font=("Arial", 9, "bold"),
        ).pack(side="left")

        self.render_comments(p_frame, post_id)

        act_frame = tk.Frame(p_frame, bg="#FFFFFF")
        act_frame.pack(fill="x", pady=(6, 0))

        tk.Button(
            act_frame,
            text="Thích",
            command=lambda pid=post_id: self.like_post(pid),
            bg="#E8F1F5",
            fg="#2C3E50",
            font=("Arial", 9, "bold"),
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
        ).pack(side="left", padx=2)

        tk.Button(
            act_frame,
            text="Bình luận",
            command=lambda pid=post_id: self.comment_post(pid),
            bg="#E8F1F5",
            fg="#2C3E50",
            font=("Arial", 9, "bold"),
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
        ).pack(side="left", padx=2)

        # Nếu là bài của chính mình thì cho phép Sửa / Xóa
        if author_phone == self.current_user_phone:
            tk.Button(
                act_frame,
                text="Sửa",
                command=lambda pid=post_id, c=content: self.edit_post(pid, c or ""),
                bg="#D1FAE5",
                fg="#065F46",
                font=("Arial", 9, "bold"),
                bd=0,
                padx=10,
                pady=5,
                cursor="hand2",
            ).pack(side="right", padx=2)

            tk.Button(
                act_frame,
                text="Xóa",
                command=lambda pid=post_id: self.delete_post(pid),
                bg="#FECACA",
                fg="#7F1D1D",
                font=("Arial", 9, "bold"),
                bd=0,
                padx=10,
                pady=5,
                cursor="hand2",
            ).pack(side="right", padx=2)


    def render_comments(self, parent, post_id):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT author_name, content FROM comments WHERE post_id=? ORDER BY id ASC",
            (post_id,),
        )
        comments = cursor.fetchall()
        conn.close()

        if not comments:
            return

        cmt_box = tk.Frame(parent, bg="#F0F7F4", padx=8, pady=6)
        cmt_box.pack(fill="x", pady=5)
        for author_name, cmt_content in comments:
            tk.Label(
                cmt_box,
                text=f"{author_name}: {cmt_content}",
                bg="#F0F7F4",
                fg="#2C3E50",
                font=("Arial", 9),
                anchor="w",
                justify="left",
                wraplength=580,
            ).pack(fill="x", pady=1)

    def like_post(self, post_id):
        # Cho phép like tất cả bài, kể cả bài người khác và bài mình.
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE posts SET likes = likes + 1 WHERE id=?", (post_id,))
        conn.commit()
        conn.close()
        self.load_feed_from_db()

    def comment_post(self, post_id):
        # Cho phép comment tất cả bài đang hiển thị. Không lọc theo chủ bài viết.
        user_cmt = simpledialog.askstring("Bình luận", "Nhập nội dung bình luận:", parent=self.root)
        if not user_cmt or not user_cmt.strip():
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO comments (post_id, author_phone, author_name, content, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                post_id,
                self.current_user_phone,
                self.current_user_name,
                user_cmt.strip(),
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
        )
        conn.commit()
        conn.close()
        self.load_feed_from_db()

    

# ================= 4. WINDOW: CHAT SYSTEM =================
class ChatWindowComponent:
    def __init__(self, parent, my_phone, partner_phone, partner_name, image_store, avatar_refs, embedded=False):
        print(f"[DEBUG] Mở chat với {partner_name} ({partner_phone}) - Embedded: {embedded}")
        
        # ĐÃ XÓA 3 DÒNG LỆNH BỊ TRÙNG LẶP Ở KHU VỰC NÀY
        
        """
        parent: nếu embedded=True thì là Frame; nếu embedded=False thì là Toplevel
        """
        self.embedded = embedded
        self.parent = parent
        self.my_phone = my_phone
        self.partner_phone = partner_phone
        self.partner_name = partner_name
        self.image_store = image_store
        self.avatar_refs = avatar_refs

        self.selected_image_path = None
        self.preview_photo = None
        self.mask_var = tk.BooleanVar(value=False)
        self.last_msg_count = -1

        if self.embedded:
            # Dùng parent làm gốc
            self.window = parent
        else:
            # Nếu muốn vẫn dùng kiểu cửa sổ riêng
            self.window = tk.Toplevel(parent)
            self.window.title(f"Nhắn tin với {partner_name}")
            self.window.geometry("450x600")
            self.window.minsize(380, 500)
            self.window.configure(bg="#E8F1F5")

        # BA DÒNG NÀY PHẢI ĐẶT Ở CUỐI CÙNG (Sau khi self.window đã có)
        self.build_ui()
        self.load_chat_history(force=True)
        self.start_auto_refresh()


    def build_ui(self):
        # Xóa hết để tránh xung đột
        for widget in self.window.winfo_children():
            widget.destroy()

        # ================= 1. HEADER (Vẽ đầu tiên trên cùng) =================
        header = tk.Frame(self.window, bg="#D8E2DC", height=50, bd=1, relief="groove")
        header.pack(fill="x", side="top", padx=0, pady=0)
        header.pack_propagate(False)

        self.render_partner_avatar(header)
        tk.Label(
            header,
            text=f"Trò chuyện với: {self.partner_name}",
            bg="#D8E2DC",
            fg="#2C3E50",
            font=("Arial", 11, "bold"),
        ).pack(side="left", padx=10, pady=12)

        # ================= 2. INPUT AREA (Vẽ thứ hai, ép nó nằm dưới đáy) =================
        bottom = tk.Frame(self.window, bg="#D8E2DC", pady=8, padx=10)
        bottom.pack(fill="x", side="bottom")

        # Preview image
        self.preview_frame = tk.Frame(bottom, bg="#FFFFFF")
        self.preview_frame.pack_forget()

        self.preview_label = tk.Label(self.preview_frame, bg="#FFFFFF")
        self.preview_label.pack(side="left", padx=5, pady=5)
        self.preview_file_label = tk.Label(self.preview_frame, text="", bg="#FFFFFF", fg="#2C3E50", font=("Arial", 9))
        self.preview_file_label.pack(side="left")

        tk.Checkbutton(
            self.preview_frame, text="Ẩn ảnh", variable=self.mask_var,
            bg="#FFFFFF", font=("Arial", 9)
        ).pack(side="left", padx=5)

        tk.Button(
            self.preview_frame, text="✕", command=self.remove_image,
            bg="#FFADAD", fg="#780000", bd=0, cursor="hand2"
        ).pack(side="right", padx=5)

        # Input row
        input_row = tk.Frame(bottom, bg="#D8E2DC")
        input_row.pack(fill="x", pady=(5, 0))

        tk.Button(
            input_row, text="Ảnh", command=self.choose_image,
            bg="#E8F1F5", fg="#2C3E50", font=("Arial", 10), bd=1, relief="groove", padx=10, pady=5
        ).pack(side="left", padx=(0, 5))

        self.entry = tk.Entry(
            input_row, bg="#FFFFFF", fg="#2C3E50", font=("Arial", 12), bd=1, relief="solid"
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=5, ipady=8)
        self.entry.bind("<Return>", self.send_message_event)
        self.entry.focus_set()

        tk.Button(
            input_row, text="Gửi", command=self.send_message,
            bg="#A8DADC", fg="#1D3557", font=("Arial", 10, "bold"), bd=0, padx=15, pady=6, cursor="hand2"
        ).pack(side="right")

        # ================= 3. CHAT AREA (Vẽ cuối cùng để nó tự lấp đầy khoảng trống) =================
        chat_container = tk.Frame(self.window, bg="#E8F1F5")
        chat_container.pack(fill="both", expand=True, side="top", padx=5, pady=5)

        self.canvas = tk.Canvas(chat_container, bg="#E8F1F5", highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(chat_container, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")

        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.chat_frame = tk.Frame(self.canvas, bg="#E8F1F5")
        self.chat_window_obj = self.canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")

        self.chat_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.chat_window_obj, width=e.width))

        # --- Bổ sung tính năng lăn chuột (MouseWheel) ---
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bound_to_mousewheel(event):
            self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbound_to_mousewheel(event):
            self.canvas.unbind_all("<MouseWheel>")

        # Chỉ kích hoạt cuộn chuột khi rê chuột vào khu vực chat
        chat_container.bind("<Enter>", _bound_to_mousewheel)
        chat_container.bind("<Leave>", _unbound_to_mousewheel)


    def render_partner_avatar(self, parent):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT avatar_path FROM users WHERE phone=?", (self.partner_phone,))
        avatar = cursor.fetchone()
        conn.close()

        avatar_path = avatar[0] if avatar and avatar[0] else ""
        if avatar_path and os.path.exists(avatar_path):
            try:
                img = Image.open(avatar_path).resize((30, 30))
                photo = ImageTk.PhotoImage(img)
                self.avatar_refs[f"chat_{self.partner_phone}"] = photo
                tk.Label(parent, image=photo, bg="#D8E2DC").pack(side="left", padx=(15, 0), pady=10)
                return
            except Exception:
                pass

        tk.Label(
            parent,
            text=self.partner_name[0].upper() if self.partner_name else "?",
            bg="#F4F1DE",
            fg="#2C3E50",
            font=("Arial", 9, "bold"),
            width=3,
            height=1,
        ).pack(side="left", padx=(15, 0), pady=10)

    def choose_image(self):
        file_path = filedialog.askopenfilename(
            title="Chọn ảnh",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")],
        )
        if not file_path:
            return

        self.selected_image_path = file_path
        img = Image.open(file_path)
        img.thumbnail((60, 60))
        self.preview_photo = ImageTk.PhotoImage(img)
        self.preview_label.config(image=self.preview_photo)
        self.preview_file_label.config(text=os.path.basename(file_path))
        self.preview_frame.pack(fill="x", pady=3)

    def remove_image(self):
        self.selected_image_path = None
        self.preview_photo = None
        self.mask_var.set(False)
        self.preview_label.config(image="")
        self.preview_file_label.config(text="")
        self.preview_frame.pack_forget()

    def load_chat_history(self, force=False):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT sender_phone, content, image_path, mask_enabled
            FROM messages
            WHERE (sender_phone=? AND receiver_phone=?)
               OR (sender_phone=? AND receiver_phone=?)
            ORDER BY id ASC
            """,
            (self.my_phone, self.partner_phone, self.partner_phone, self.my_phone),
        )
        logs = cursor.fetchall()
        conn.close()

        if not force and len(logs) == self.last_msg_count:
            return

        self.last_msg_count = len(logs)
        for child in self.chat_frame.winfo_children():
            child.destroy()

        for sender_phone, content, image_path, mask_enabled in logs:
            is_me = sender_phone == self.my_phone
            if content:
                self.render_text_bubble(content, is_me)
            if image_path:
                self.render_image_bubble(image_path, is_me, bool(mask_enabled))

        self.scroll_bottom()

    def start_auto_refresh(self):
        if self.window.winfo_exists():
            self.load_chat_history()
            self.window.after(1000, self.start_auto_refresh)

    def render_text_bubble(self, text, is_me):
        row = tk.Frame(self.chat_frame, bg="#E8F1F5")
        row.pack(fill="x", padx=10, pady=4)

        color = "#A8DADC" if is_me else "#F4F1DE"
        fg_color = "#1D3557" if is_me else "#2C3E50"
        align = "e" if is_me else "w"

        tk.Label(
            row,
            text=text,
            bg=color,
            fg=fg_color,
            font=("Arial", 10),
            wraplength=250,
            justify="left",
            padx=12,
            pady=7,
        ).pack(anchor=align)

    def render_image_bubble(self, image_path, is_me, mask_enabled):
        if not os.path.exists(image_path):
            return

        row = tk.Frame(self.chat_frame, bg="#E8F1F5")
        row.pack(fill="x", padx=10, pady=4)

        align = "e" if is_me else "w"
        bubble_bg = "#A8DADC" if is_me else "#F4F1DE"
        container = tk.Frame(row, bg=bubble_bg, padx=6, pady=6)
        container.pack(anchor=align)

        try:
            img = Image.open(image_path)
            img.thumbnail((180, 180))
            photo = ImageTk.PhotoImage(img)
            self.image_store.append(photo)
            tk.Label(container, image=photo, bg=bubble_bg).pack()
            if mask_enabled:
                tk.Label(
                    container,
                    text="Đã ẩn dữ liệu ảnh",
                    bg=bubble_bg,
                    fg="#D97706",
                    font=("Arial", 8, "italic"),
                ).pack(anchor="w")
        except Exception:
            pass

    def send_message_event(self, event):
        self.send_message()
        return "break"

    def send_message(self):
        text = self.entry.get().strip()
        if not text and not self.selected_image_path:
            return

        mask_val = 1 if self.mask_var.get() else 0
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO messages (sender_phone, receiver_phone, content, image_path, mask_enabled, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (self.my_phone, self.partner_phone, text, self.selected_image_path, mask_val, now_str),
        )
        conn.commit()
        conn.close()

        self.entry.delete(0, "end")
        self.remove_image()
        self.load_chat_history(force=True)

    def scroll_bottom(self):
        self.window.after(50, lambda: self.canvas.yview_moveto(1.0))


# ================= RUN PROGRAM =================
if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = SocialChatApp(root)
    root.mainloop()
