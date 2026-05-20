import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import os
import re
import sqlite3
from datetime import datetime

# ================= DATABASE SYSTEM =================
DB_NAME = "social_app.db"

def init_db():
    """Khởi tạo và làm sạch cấu trúc cơ sở dữ liệu để sửa lỗi không tạo được tài khoản"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Bảng người dùng
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            phone TEXT PRIMARY KEY,
            password TEXT,
            name TEXT,
            avatar_path TEXT
        )
    ''')
    
    # Bảng bạn bè
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS friends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_phone TEXT,
            friend_phone TEXT,
            UNIQUE(user_phone, friend_phone)
        )
    ''')
    
    # Bảng bài đăng
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_phone TEXT,
            author_name TEXT,
            content TEXT,
            image_path TEXT,
            mask_enabled INTEGER,
            likes INTEGER DEFAULT 0,
            timestamp TEXT,
            FOREIGN KEY(author_phone) REFERENCES users(phone)
        )
    ''')
    
    # Bảng bình luận
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            author_name TEXT,
            content TEXT,
            FOREIGN KEY(post_id) REFERENCES posts(id)
        )
    ''')
    
    # Bảng tin nhắn chat
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_phone TEXT,
            receiver_phone TEXT,
            content TEXT,
            image_path TEXT,
            mask_enabled INTEGER,
            timestamp TEXT
        )
    ''')

    # Bảng ghi nhớ tài khoản đăng nhập
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS remember_me (
            id INTEGER PRIMARY KEY,
            phone TEXT,
            password TEXT
        )
    ''')
    
    # Sửa lỗi Yêu cầu 8 & lỗi không tạo được tài khoản: Cập nhật cột avatar_path một cách an toàn
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN avatar_path TEXT")
    except sqlite3.OperationalError:
        pass 

    # Tạo sẵn các tài khoản mẫu chuẩn để kiểm tra
    sample_users = [
        ('0911223344', '12345678', 'Nguyễn Văn A', ''),
        ('0988776655', '12345678', 'Trần Thị B', ''),
        ('0900112233', '12345678', 'Lê Hoàng C', '')
    ]
    for u in sample_users:
        cursor.execute("SELECT * FROM users WHERE phone=?", (u[0],))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?)", u)
            
    conn.commit()
    conn.close()

# ================= APPLICATION CLASS =================
class SocialChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Social Network Demo")
        self.root.geometry("980x750")
        self.root.minsize(850, 650)
        self.root.configure(bg="#E8F1F5") # Màu nền ngoài Pastel xanh dịu mắt

        self.current_user_phone = None
        self.current_user_name = None
        self.current_user_avatar = ""

        self.feed_images = {}
        self.chat_images = []
        self.avatar_refs = {} 

        self.show_login_screen()

    def clear_root(self):
        for widget in self.root.winfo_children():
            widget.pack_forget()
            widget.grid_forget()

    # ================= 1. SCREEN: LOGIN & REGISTER (PASTEL) =================
    
    def show_login_screen(self):
        self.clear_root()
        
        login_frame = tk.Frame(self.root, bg="#F0F7F4", padx=35, pady=35, bd=1, relief="solid", highlightthickness=0)
        login_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(login_frame, text="ĐĂNG NHẬP", bg="#F0F7F4", fg="#2C3E50", font=("Arial", 18, "bold")).pack(pady=(0, 25))

        tk.Label(login_frame, text="Số điện thoại:", bg="#F0F7F4", fg="#566573", font=("Arial", 10, "bold")).pack(anchor="w")
        self.ent_phone = tk.Entry(login_frame, font=("Arial", 11), width=32, bg="#FFFFFF", fg="#2C3E50", relief="groove")
        self.ent_phone.pack(pady=(5, 15), ipady=6)

        tk.Label(login_frame, text="Mật khẩu:", bg="#F0F7F4", fg="#566573", font=("Arial", 10, "bold")).pack(anchor="w")
        self.ent_pwd = tk.Entry(login_frame, font=("Arial", 11), width=32, bg="#FFFFFF", fg="#2C3E50", show="*", relief="groove")
        self.ent_pwd.pack(pady=(5, 20), ipady=6)

        # Đọc thông tin ghi nhớ đăng nhập tự động điền form
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT phone, password FROM remember_me WHERE id = 1")
        remembered = cursor.fetchone()
        conn.close()
        if remembered:
            self.ent_phone.insert(0, remembered[0])
            self.ent_pwd.insert(0, remembered[1])

        btn_login = tk.Button(login_frame, text="Đăng nhập", command=self.handle_login, bg="#A8DADC", fg="#1D3557", font=("Arial", 11, "bold"), bd=0, width=30, pady=8, cursor="hand2")
        btn_login.pack(pady=5)

        btn_reg_page = tk.Button(login_frame, text="Tạo tài khoản mới", command=self.show_register_screen, bg="#F0F7F4", fg="#457B9D", font=("Arial", 10, "underline"), bd=0, cursor="hand2")
        btn_reg_page.pack(pady=5)

    def show_register_screen(self):
        self.clear_root()

        reg_frame = tk.Frame(self.root, bg="#F0F7F4", padx=35, pady=35, bd=1, relief="solid")
        reg_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(reg_frame, text="ĐĂNG KÝ TÀI KHOẢN", bg="#F0F7F4", fg="#2C3E50", font=("Arial", 16, "bold")).pack(pady=(0, 25))

        tk.Label(reg_frame, text="Tên hiển thị:", bg="#F0F7F4", fg="#566573", font=("Arial", 10, "bold")).pack(anchor="w")
        self.ent_reg_name = tk.Entry(reg_frame, font=("Arial", 11), width=32, bg="#FFFFFF", fg="#2C3E50", relief="groove")
        self.ent_reg_name.pack(pady=(5, 12), ipady=6)

        tk.Label(reg_frame, text="Số điện thoại Việt Nam:", bg="#F0F7F4", fg="#566573", font=("Arial", 10, "bold")).pack(anchor="w")
        self.ent_reg_phone = tk.Entry(reg_frame, font=("Arial", 11), width=32, bg="#FFFFFF", fg="#2C3E50", relief="groove")
        self.ent_reg_phone.pack(pady=(5, 12), ipady=6)

        tk.Label(reg_frame, text="Mật khẩu (>= 8 ký tự):", bg="#F0F7F4", fg="#566573", font=("Arial", 10, "bold")).pack(anchor="w")
        self.ent_reg_pwd = tk.Entry(reg_frame, font=("Arial", 11), width=32, bg="#FFFFFF", fg="#2C3E50", show="*", relief="groove")
        self.ent_reg_pwd.pack(pady=(5, 20), ipady=6)

        # Cài đặt ảnh đại diện tài khoản
        self.reg_avatar_path = ""
        def choose_reg_avatar():
            path = filedialog.askopenfilename(title="Chọn ảnh đại diện", filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")])
            if path:
                self.reg_avatar_path = path
                lbl_path_status.config(text=os.path.basename(path), fg="#1D3557")

        btn_avatar = tk.Button(reg_frame, text="🖼 Tải lên ảnh đại diện (Tùy chọn)", command=choose_reg_avatar, bg="#E8F1F5", fg="#2C3E50", font=("Arial", 9))
        btn_avatar.pack(pady=(0, 2))
        lbl_path_status = tk.Label(reg_frame, text="Chưa chọn ảnh", bg="#F0F7F4", fg="#9CA3AF", font=("Arial", 8, "italic"))
        lbl_path_status.pack(pady=(0, 15))

        btn_submit_reg = tk.Button(reg_frame, text="Đăng ký", command=self.handle_register, bg="#A8E6CF", fg="#1D3557", font=("Arial", 11, "bold"), bd=0, width=30, pady=8, cursor="hand2")
        btn_submit_reg.pack(pady=5)

        btn_back = tk.Button(reg_frame, text="Quay lại đăng nhập", command=self.show_login_screen, bg="#F0F7F4", fg="#566573", font=("Arial", 10), bd=0, cursor="hand2")
        btn_back.pack(pady=5)

    def validate_user_inputs(self, phone, pwd):
        phone_regex = r"^(03|05|07|08|09)\d{8}$"
        if not re.match(phone_regex, phone):
            messagebox.showerror("Lỗi dữ liệu", "Số điện thoại không hợp lệ! Vui lòng nhập số điện thoại Việt Nam (10 chữ số).")
            return False
        if len(pwd) < 8:
            messagebox.showerror("Lỗi dữ liệu", "Mật khẩu bảo mật phải từ 8 ký tự trở lên!")
            return False
        return True

    def handle_login(self):
        phone = self.ent_phone.get().strip()
        pwd = self.ent_pwd.get().strip()

        if not self.validate_user_inputs(phone, pwd):
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE phone=? AND password=?", (phone, pwd))
        user = cursor.fetchone()
        
        if user:
            # Ghi nhớ đăng nhập
            cursor.execute("DELETE FROM remember_me")
            cursor.execute("INSERT INTO remember_me (id, phone, password) VALUES (1, ?, ?)", (phone, pwd))
            conn.commit()
            conn.close()

            self.current_user_phone = user[0]
            self.current_user_name = user[2]
            self.current_user_avatar = user[3] if len(user) > 3 and user[3] else ""
            self.build_main_ui()
        else:
            conn.close()
            messagebox.showerror("Thất bại", "Số điện thoại hoặc mật khẩu chưa chính xác!")

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
        
        # Check xem SĐT đã tồn tại chưa
        cursor.execute("SELECT phone FROM users WHERE phone=?", (phone,))
        if cursor.fetchone():
            messagebox.showerror("Lỗi", "Số điện thoại này đã tồn tại trên hệ thống!")
            conn.close()
            return

        try:
            cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (phone, pwd, name, self.reg_avatar_path))
            conn.commit()
            messagebox.showinfo("Thành công", "Đăng ký thành công! Hãy đăng nhập hệ thống.")
            self.show_login_screen()
        except sqlite3.IntegrityError:
            messagebox.showerror("Lỗi", "Số điện thoại này đã tồn tại trên hệ thống!")
        finally:
            conn.close()

    def handle_logout_clear(self):
        """Sửa lỗi Đăng xuất: Xóa toàn bộ dữ liệu tạm thời, xóa bảng ghi nhớ để đăng nhập được tài khoản mới mà không bị lỗi"""
        self.current_user_phone = None
        self.current_user_name = None
        self.current_user_avatar = ""
        self.avatar_refs.clear()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM remember_me")
        conn.commit()
        conn.close()
        
        self.show_login_screen()
        self.ent_phone.delete(0, "end")
        self.ent_pwd.delete(0, "end")

    # ================= 2. SCREEN: MAIN SOCIAL FEED & SIDEBAR SYSTEM =================

    def build_main_ui(self):
        self.clear_root()

        self.post_image_path = None
        self.post_preview_photo = None
        self.post_mask_var = tk.BooleanVar(value=False)

        header = tk.Frame(self.root, bg="#D8E2DC", height=60, bd=1, relief="groove")
        header.pack(fill="x")
        header.pack_propagate(False)

        if self.current_user_avatar and os.path.exists(self.current_user_avatar):
            img_av = Image.open(self.current_user_avatar).resize((32, 32))
            photo_av = ImageTk.PhotoImage(img_av)
            self.avatar_refs["me"] = photo_av
            lbl_av_img = tk.Label(header, image=photo_av, bg="#D8E2DC")
            lbl_av_img.pack(side="left", padx=(15, 0), pady=14)
        else:
            lbl_av_txt = tk.Label(header, text=self.current_user_name[0].upper(), bg="#A8DADC", fg="#1D3557", font=("Arial", 10, "bold"), width=3, height=1)
            lbl_av_txt.pack(side="left", padx=(15, 0), pady=14)

        title = tk.Label(header, text=f" Mạng Xã Hội  |  {self.current_user_name}", bg="#D8E2DC", fg="#2C3E50", font=("Arial", 13, "bold"))
        title.pack(side="left", padx=5, pady=15)

        btn_logout = tk.Button(header, text="Đăng xuất", command=self.handle_logout_clear, bg="#FFADAD", fg="#780000", font=("Arial", 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2")
        btn_logout.pack(side="right", padx=20, pady=12)

        chat_button = tk.Button(header, text="💬 Nhắn tin trò chuyện", command=self.show_select_chat_partner, bg="#A8DADC", fg="#1D3557", font=("Arial", 10, "bold"), bd=0, padx=14, pady=6, cursor="hand2")
        chat_button.pack(side="right", padx=5, pady=12)

        main_content = tk.Frame(self.root, bg="#E8F1F5")
        main_content.pack(fill="both", expand=True)

        sidebar = tk.Frame(main_content, bg="#F4F1DE", width=240, bd=1, relief="groove")
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        search_box = tk.LabelFrame(sidebar, text="🔍 Tìm bạn bằng SĐT", bg="#F4F1DE", fg="#2C3E50", font=("Arial", 10, "bold"), padx=10, pady=10)
        search_box.pack(fill="x", padx=12, pady=15)

        self.ent_search_phone = tk.Entry(search_box, font=("Arial", 10), bg="#FFFFFF", fg="#2C3E50", relief="sunken")
        self.ent_search_phone.pack(fill="x", ipady=4, pady=(0, 8))

        btn_search_friend = tk.Button(search_box, text="Tìm & Kết bạn", command=self.handle_add_friend, bg="#E9C46A", fg="#1D3557", font=("Arial", 9, "bold"), bd=0, pady=5, cursor="hand2")
        btn_search_friend.pack(fill="x")

        tk.Label(sidebar, text="👥 Bạn bè của bạn:", bg="#F4F1DE", fg="#566573", font=("Arial", 10, "bold")).pack(anchor="w", padx=15, pady=(10, 2))
        
        self.friend_list_frame = tk.Frame(sidebar, bg="#F4F1DE")
        self.friend_list_frame.pack(fill="both", expand=True, padx=15)
        self.update_sidebar_friends()

        feed_container = tk.Frame(main_content, bg="#E8F1F5")
        feed_container.pack(side="left", fill="both", expand=True, padx=15, pady=15)

        self.feed_canvas = tk.Canvas(feed_container, bg="#E8F1F5", highlightthickness=0)
        self.feed_canvas.pack(side="left", fill="both", expand=True)

        feed_scrollbar = tk.Scrollbar(feed_container, orient="vertical", command=self.feed_canvas.yview)
        feed_scrollbar.pack(side="right", fill="y")
        self.feed_canvas.configure(yscrollcommand=feed_scrollbar.set)

        self.feed_frame = tk.Frame(self.feed_canvas, bg="#E8F1F5")
        self.feed_window = self.feed_canvas.create_window((0, 0), window=self.feed_frame, anchor="nw")

        self.feed_frame.bind("<Configure>", lambda e: self.feed_canvas.configure(scrollregion=self.feed_canvas.bbox("all")))
        self.feed_canvas.bind("<Configure>", lambda e: self.feed_canvas.itemconfig(self.feed_window, width=e.width))

        self.create_post_box()
        self.load_feed_from_db()

    def handle_add_friend(self):
        """Hiện người dùng ra để chọn có kết bạn hay không"""
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
            messagebox.showerror("Không tìm thấy", "Không có người dùng nào sử dụng Số điện thoại này!")
            conn.close()
            return
            
        friend_name = user_found[0]

        cursor.execute("SELECT id FROM friends WHERE user_phone=? AND friend_phone=?", (self.current_user_phone, target_phone))
        already_friend = cursor.fetchone()

        if already_friend:
            messagebox.showinfo("Thông báo", f"Bạn và {friend_name} đã là bạn bè từ trước!")
            conn.close()
            return

        confirm = messagebox.askyesno("Xác nhận kết bạn", f"Hệ thống tìm thấy người dùng:\nTên: {friend_name}\nSĐT: {target_phone}\n\nBạn có muốn kết bạn với người này không?")
        if confirm:
            cursor.execute("INSERT INTO friends (user_phone, friend_phone) VALUES (?, ?)", (self.current_user_phone, target_phone))
            cursor.execute("INSERT INTO friends (user_phone, friend_phone) VALUES (?, ?)", (target_phone, self.current_user_phone))
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
        cursor.execute('''
            SELECT users.name, users.phone 
            FROM friends 
            JOIN users ON friends.friend_phone = users.phone 
            WHERE friends.user_phone = ?
        ''', (self.current_user_phone,))
        friend_rows = cursor.fetchall()
        conn.close()

        if not friend_rows:
            tk.Label(self.friend_list_frame, text="(Chưa có bạn bè,\nhãy tìm kiếm ở trên)", bg="#F4F1DE", fg="#9CA3AF", font=("Arial", 9, "italic"), justify="left").pack(anchor="w", pady=5)
        else:
            for name, phone in friend_rows:
                f_lbl = tk.Label(self.friend_list_frame, text=f"• {name}", bg="#F4F1DE", fg="#2C3E50", font=("Arial", 10), anchor="w")
                f_lbl.pack(fill="x", pady=2)

    def create_post_box(self):
        box = tk.Frame(self.feed_frame, bg="#F0F7F4", padx=16, pady=14, bd=1, relief="solid", highlightthickness=0)
        box.pack(fill="x", pady=(0, 16))

        tk.Label(box, text="✍️ Đăng bài viết mới", bg="#F0F7F4", fg="#2C3E50", font=("Arial", 11, "bold")).pack(anchor="w")

        self.post_text = tk.Text(box, height=3, font=("Arial", 11), bg="#FFFFFF", fg="#2C3E50", bd=1, relief="solid", padx=10, pady=8, wrap="word")
        self.post_text.pack(fill="x", pady=10)

        self.post_preview_frame = tk.Frame(box, bg="#FFFFFF")
        self.post_preview_frame.pack_forget()

        self.post_preview_label = tk.Label(self.post_preview_frame, bg="#FFFFFF")
        self.post_preview_label.pack(side="left", padx=5, pady=5)

        self.post_file_label = tk.Label(self.post_preview_frame, text="", bg="#FFFFFF", fg="#2C3E50", font=("Arial", 9))
        self.post_file_label.pack(side="left", padx=5)

        btn_del_img = tk.Button(self.post_preview_frame, text="✕", command=self.remove_post_image, bg="#FFADAD", fg="#780000", bd=0, padx=5, cursor="hand2")
        btn_del_img.pack(side="right", padx=5)

        action_row = tk.Frame(box, bg="#F0F7F4")
        action_row.pack(fill="x")

        btn_img = tk.Button(action_row, text="🖼 Thêm ảnh", command=self.choose_post_image, bg="#E8F1F5", fg="#2C3E50", font=("Arial", 10), bd=1, relief="groove", padx=10, pady=5, cursor="hand2")
        btn_img.pack(side="left")

        mask_check = tk.Checkbutton(action_row, text="Che dữ liệu", variable=self.post_mask_var, bg="#F0F7F4", fg="#2C3E50", font=("Arial", 10))
        mask_check.pack(side="left", padx=10)

        btn_pub = tk.Button(action_row, text="Đăng bài", command=self.publish_post, bg="#A8DADC", fg="#1D3557", font=("Arial", 10, "bold"), bd=0, padx=16, pady=6, cursor="hand2")
        btn_pub.pack(side="right")

    def choose_post_image(self):
        file_path = filedialog.askopenfilename(title="Chọn hình ảnh", filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if not file_path: return
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
            "INSERT INTO posts (author_phone, author_name, content, image_path, mask_enabled, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (self.current_user_phone, self.current_user_name, content, self.post_image_path, mask_val, now_str)
        )
        conn.commit()
        conn.close()

        self.post_text.delete("1.0", "end")
        self.remove_post_image()
        self.post_mask_var.set(False)
        self.load_feed_from_db()

    def load_feed_from_db(self):
        """Sửa Yêu cầu 11: Cho phép hiển thị bài đăng của bản thân và bài đăng của người khác để có thể tương tác chéo"""
        for child in self.feed_frame.winfo_children():
            if child != self.feed_frame.winfo_children()[0]:
                child.destroy()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT posts.id, posts.author_name, posts.content, posts.image_path, posts.mask_enabled, posts.likes, posts.timestamp, users.avatar_path 
            FROM posts 
            LEFT JOIN users ON posts.author_phone = users.phone
            ORDER BY posts.id DESC
        ''')
        posts = cursor.fetchall()
        conn.close()

        for p in posts:
            self.render_post_item(p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7])

    def render_post_item(self, post_id, author, content, img_path, mask_enabled, likes, time_str, author_avatar):
        p_frame = tk.Frame(self.feed_frame, bg="#FFFFFF", padx=14, pady=12, bd=1, relief="solid", highlightthickness=0)
        p_frame.pack(fill="x", pady=(0, 12))

        top = tk.Frame(p_frame, bg="#FFFFFF")
        top.pack(fill="x")

        if author_avatar and os.path.exists(author_avatar):
            img_av = Image.open(author_avatar).resize((32, 32))
            photo_av = ImageTk.PhotoImage(img_av)
            self.avatar_refs[f"post_{post_id}"] = photo_av
            lbl_avt = tk.Label(top, image=photo_av, bg="#FFFFFF")
        else:
            lbl_avt = tk.Label(top, text=author[0].upper(), bg="#A8DADC", fg="#1D3557", font=("Arial", 10, "bold"), width=3, height=1)
        lbl_avt.pack(side="left")

        info_f = tk.Frame(top, bg="#FFFFFF")
        info_f.pack(side="left", padx=8)
        tk.Label(info_f, text=author, bg="#FFFFFF", fg="#2C3E50", font=("Arial", 11, "bold")).pack(anchor="w")
        tk.Label(info_f, text=time_str, bg="#FFFFFF", fg="#6B7280", font=("Arial", 8)).pack(anchor="w")

        if content:
            tk.Label(p_frame, text=content, bg="#FFFFFF", fg="#2C3E50", font=("Arial", 11), justify="left", wrap=500).pack(anchor="w", pady=8)

        if img_path and os.path.exists(img_path):
            try:
                img = Image.open(img_path)
                img.thumbnail((450, 300))
                photo = ImageTk.PhotoImage(img)
                self.feed_images[f"p_{post_id}"] = photo

                lbl_img = tk.Label(p_frame, image=photo, bg="#FFFFFF")
                lbl_img.pack(anchor="w", pady=5)
            except:
                pass

        if mask_enabled:
            tk.Label(p_frame, text="🔒 Bài viết được ẩn thông tin nhạy cảm", bg="#F4F1DE", fg="#D97706", font=("Arial", 9, "italic")).pack(anchor="w", pady=4)

        stats_frame = tk.Frame(p_frame, bg="#FFFFFF")
        stats_frame.pack(fill="x", pady=4)
        lbl_likes_count = tk.Label(stats_frame, text=f"❤️ {likes} lượt thích", bg="#FFFFFF", fg="#457B9D", font=("Arial", 9, "bold"))
        lbl_likes_count.pack(side="left")

        conn = sqlite3.connect(DB_NAME)
        c_cursor = conn.cursor()
        c_cursor.execute("SELECT author_name, content FROM comments WHERE post_id=?", (post_id,))
        comments = c_cursor.fetchall()
        conn.close()

        if comments:
            cmt_box = tk.Frame(p_frame, bg="#F0F7F4", padx=8, pady=6)
            cmt_box.pack(fill="x", pady=5)
            for cmt in comments:
                tk.Label(cmt_box, text=f"{cmt[0]}: {cmt[1]}", bg="#F0F7F4", fg="#2C3E50", font=("Arial", 9.5), anchor="w").pack(fill="x", pady=1)

        act_frame = tk.Frame(p_frame, bg="#FFFFFF")
        act_frame.pack(fill="x", pady=(6, 0))

        # Yêu cầu 11: Sửa hàm lưu tương tác để người khác thấy mình thả tim/bình luận đồng bộ
        def trigger_like():
            conn_l = sqlite3.connect(DB_NAME)
            cur_l = conn_l.cursor()
            cur_l.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
            conn_l.commit()
            conn_l.close()
            self.load_feed_from_db()

        def trigger_comment():
            user_cmt = simpledialog.askstring("Bình luận", "Nhập nội dung bình luận:")
            if user_cmt and user_cmt.strip():
                conn_c = sqlite3.connect(DB_NAME)
                cur_c = conn_c.cursor()
                cur_c.execute("INSERT INTO comments (post_id, author_name, content) VALUES (?, ?, ?)", (post_id, self.current_user_name, user_cmt.strip()))
                conn_c.commit()
                conn_c.close()
                self.load_feed_from_db()

        tk.Button(act_frame, text="👍 Thích", command=trigger_like, bg="#E8F1F5", fg="#2C3E50", font=("Arial", 9, "bold"), bd=0, padx=12, pady=5, cursor="hand2").pack(side="left", padx=2)
        tk.Button(act_frame, text="💬 Bình luận", command=trigger_comment, bg="#E8F1F5", fg="#2C3E50", font=("Arial", 9, "bold"), bd=0, padx=12, pady=5, cursor="hand2").pack(side="left", padx=2)

    # ================= 3. FEATURE: CHOOSE CHAT PARTNER FROM FRIENDS =================

    def show_select_chat_partner(self):
        select_win = tk.Toplevel(self.root)
        select_win.title("Chọn người muốn nhắn tin")
        select_win.geometry("350x400")
        select_win.configure(bg="#F4F1DE")
        select_win.transient(self.root)
        select_win.grab_set()

        tk.Label(select_win, text="Danh sách bạn bè", bg="#F4F1DE", fg="#2C3E50", font=("Arial", 12, "bold")).pack(pady=15)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT users.name, users.phone 
            FROM friends 
            JOIN users ON friends.friend_phone = users.phone 
            WHERE friends.user_phone = ?
        ''', (self.current_user_phone,))
        friends = cursor.fetchall()
        conn.close()

        if not friends:
            tk.Label(select_win, text="Bạn chưa có bạn bè nào.\nHãy kết bạn trước bằng ô tìm kiếm!", bg="#F4F1DE", fg="#6B7280", font=("Arial", 10), justify="center").pack(pady=40)
            return

        list_f = tk.Frame(select_win, bg="#F4F1DE")
        list_f.pack(fill="both", expand=True, padx=20)

        for name, phone in friends:
            def open_chat(p_phone=phone, p_name=name):
                select_win.destroy()
                self.open_chat_window(p_phone, p_name)

            btn_partner = tk.Button(list_f, text=f"💬 {name} ({phone})", command=open_chat, bg="#E8F1F5", fg="#2C3E50", font=("Arial", 10), bd=0, anchor="w", padx=15, pady=8, cursor="hand2")
            btn_partner.pack(fill="x", pady=4)

    def open_chat_window(self, partner_phone, partner_name):
        chat_win = tk.Toplevel(self.root)
        chat_win.title(f"Nhắn tin với {partner_name}")
        chat_win.geometry("450x600")
        chat_win.minsize(380, 500)
        chat_win.configure(bg="#E8F1F5")

        ChatWindowComponent(chat_win, self.current_user_phone, partner_phone, partner_name, self.chat_images, self.avatar_refs)


# ================= 4. WINDOW: CHAT SYSTEM (PASTEL MODE) =================

class ChatWindowComponent:
    def __init__(self, window, my_phone, partner_phone, partner_name, image_store, avatar_refs):
        self.window = window
        self.my_phone = my_phone
        self.partner_phone = partner_phone
        self.partner_name = partner_name
        self.image_store = image_store
        self.avatar_refs = avatar_refs

        self.selected_image_path = None
        self.preview_photo = None
        self.mask_var = tk.BooleanVar(value=False)
        self.last_msg_count = 0 

        self.build_ui()
        self.load_chat_history()
        self.start_auto_refresh() 

    def build_ui(self):
        """Sửa Yêu cầu 6: Sắp xếp lại giao diện bằng pack() chuẩn để ô nhập dữ liệu và nút Gửi không bao giờ bị biến mất"""
        header = tk.Frame(self.window, bg="#D8E2DC", height=50, bd=1, relief="groove")
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT avatar_path FROM users WHERE phone=?", (self.partner_phone,))
        p_av = cursor.fetchone()
        conn.close()

        if p_av and p_av[0] and os.path.exists(p_av[0]):
            img_p = Image.open(p_av[0]).resize((30, 30))
            photo_p = ImageTk.PhotoImage(img_p)
            self.avatar_refs[f"chat_{self.partner_phone}"] = photo_p
            lbl_p_av = tk.Label(header, image=photo_p, bg="#D8E2DC")
            lbl_p_av.pack(side="left", padx=(15, 0), pady=10)
        else:
            lbl_p_av = tk.Label(header, text=self.partner_name[0].upper(), bg="#F4F1DE", fg="#2C3E50", font=("Arial", 9, "bold"), width=3, height=1)
            lbl_p_av.pack(side="left", padx=(15, 0), pady=10)

        tk.Label(header, text=f" Trò chuyện với: {self.partner_name}", bg="#D8E2DC", fg="#2C3E50", font=("Arial", 11, "bold")).pack(side="left", padx=5, pady=12)

        # Thanh dưới chứa ô nhập liệu đóng gói trước lên đáy cửa sổ
        bottom = tk.Frame(self.window, bg="#D8E2DC", pady=8, padx=10)
        bottom.pack(fill="x", side="bottom")

        self.preview_frame = tk.Frame(bottom, bg="#FFFFFF")
        self.preview_frame.pack_forget()

        self.preview_label = tk.Label(self.preview_frame, bg="#FFFFFF")
        self.preview_label.pack(side="left", padx=5, pady=5)
        self.preview_file_label = tk.Label(self.preview_frame, text="", bg="#FFFFFF", fg="#2C3E50", font=("Arial", 9))
        self.preview_file_label.pack(side="left")

        tk.Checkbutton(self.preview_frame, text="Ẩn ảnh", variable=self.mask_var, bg="#FFFFFF", font=("Arial", 9)).pack(side="left", padx=5)
        tk.Button(self.preview_frame, text="✕", command=self.remove_image, bg="#FFADAD", fg="#780000", bd=0, cursor="hand2").pack(side="right", padx=5)

        input_row = tk.Frame(bottom, bg="#D8E2DC")
        input_row.pack(fill="x")

        tk.Button(input_row, text="🖼 Ảnh", command=self.choose_image, bg="#E8F1F5", fg="#2C3E50", font=("Arial", 10), bd=1, relief="groove", padx=10, pady=5, cursor="hand2").pack(side="left", padx=(0, 5))

        # Ô nhập text (Khôi phục Entry chuẩn và hiển thị rõ ràng cố định)
        self.entry = tk.Entry(input_row, bg="#FFFFFF", fg="#2C3E50", font=("Arial", 12), bd=1, relief="solid", padx=8)
        self.entry.pack(side="left", fill="x", expand=True, padx=2, ipady=8)
        
        # Nhấn Enter để gửi tin nhắn đi ngay lập tức
        self.entry.bind("<Return>", lambda event: self.send_message())

        # Nút Gửi luôn hiển thị cố định bên phải ô nhập
        btn_send = tk.Button(input_row, text="Gửi", command=self.send_message, bg="#A8DADC", fg="#1D3557", font=("Arial", 10, "bold"), bd=0, padx=15, pady=6, cursor="hand2")
        btn_send.pack(side="right", padx=(5, 0))

        # Khung Canvas chứa nội dung chat chiếm trọn phần diện tích ở giữa còn lại
        self.canvas = tk.Canvas(self.window, bg="#E8F1F5", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.chat_frame = tk.Frame(self.canvas, bg="#E8F1F5")
        self.chat_window_obj = self.canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")

        self.chat_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.chat_window_obj, width=e.width))

    def choose_image(self):
        file_path = filedialog.askopenfilename(title="Chọn ảnh", filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if not file_path: return
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
        self.preview_frame.pack_forget()

    def load_chat_history(self):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT sender_phone, content, image_path, mask_enabled 
            FROM messages 
            WHERE (sender_phone=? AND receiver_phone=?) OR (sender_phone=? AND receiver_phone=?)
            ORDER BY id ASC
        ''', (self.my_phone, self.partner_phone, self.partner_phone, self.my_phone))
        logs = cursor.fetchall()
        conn.close()

        if len(logs) == self.last_msg_count:
            return

        self.last_msg_count = len(logs)
        for child in self.chat_frame.winfo_children():
            child.destroy()

        for msg in logs:
            is_me = (msg[0] == self.my_phone)
            if msg[1]:
                self.render_text_bubble(msg[1], is_me)
            if msg[2]:
                self.render_image_bubble(msg[2], is_me, bool(msg[3]))

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

        lbl = tk.Label(row, text=text, bg=color, fg=fg_color, font=("Arial", 10), wraplength=250, justify="left", padx=12, pady=7)
        lbl.pack(anchor=align)

    def render_image_bubble(self, image_path, is_me, mask_enabled):
        if not os.path.exists(image_path): return
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
                tk.Label(container, text="🔒 Đã ẩn dữ liệu ảnh", bg=bubble_bg, fg="#D97706", font=("Arial", 8, "italic")).pack(anchor="w")
        except:
            pass

    def send_message(self):
        text = self.entry.get().strip()
        if not text and not self.selected_image_path: return

        mask_val = 1 if self.mask_var.get() else 0
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (sender_phone, receiver_phone, content, image_path, mask_enabled, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (self.my_phone, self.partner_phone, text, self.selected_image_path, mask_val, now_str)
        )
        conn.commit()
        conn.close()

        self.entry.delete(0, "end")
        self.remove_image()
        self.load_chat_history()

    def scroll_bottom(self):
        self.window.after(50, lambda: self.canvas.yview_moveto(1.0))


# ================= RUN PROGRAM =================
if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = SocialChatApp(root)
    root.mainloop()