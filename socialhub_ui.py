import os
import platform      # Thêm dòng này
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk


THEME = {
    "bg": "#F0F2F5",
    "surface": "#FFFFFF",
    "surface_2": "#F7F9FC",
    "line": "#E5E7EB",
    "text": "#111827",
    "muted": "#6B7280",
    "primary": "#1877F2",
    "primary_dark": "#0F5EC7",
    "primary_soft": "#E7F0FF",
    "danger": "#EF4444",
    "danger_soft": "#FEE2E2",
    "success": "#16A34A",
    "warning_soft": "#FFF7ED",
    "bubble_me": "#1877F2",
    "bubble_other": "#FFFFFF",
}

FONT = "Arial"


def hand(widget):
    try:
        widget.configure(cursor="hand2")
    except tk.TclError:
        pass
    return widget

def open_document(filepath):
    """Hàm hỗ trợ mở file bằng ứng dụng mặc định của hệ điều hành (ví dụ: MS Word)"""
    if not os.path.exists(filepath):
        messagebox.showerror("Lỗi", "Không tìm thấy file trên hệ thống!")
        return
    try:
        if platform.system() == 'Windows':
            os.startfile(filepath)
        elif platform.system() == 'Darwin':  # macOS
            subprocess.call(('open', filepath))
        else:  # Linux
            subprocess.call(('xdg-open', filepath))
    except Exception as e:
        messagebox.showerror("Lỗi", f"Không thể mở file: {e}")
        
def make_button(parent, text, command=None, variant="primary", width=None):
    colors = {
        "primary": (THEME["primary"], "#FFFFFF", THEME["primary_dark"]),
        "soft": (THEME["surface_2"], THEME["text"], THEME["primary_soft"]),
        "ghost": (THEME["surface"], THEME["primary"], THEME["primary_soft"]),
        "danger": (THEME["danger_soft"], "#991B1B", "#FCA5A5"),
        "success": ("#DCFCE7", "#166534", "#BBF7D0"),
    }
    bg, fg, active = colors.get(variant, colors["primary"])

    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        activebackground=active,
        activeforeground=fg,
        font=(FONT, 10, "bold"),
        bd=0,
        relief="flat",
        padx=14,
        pady=9,
        width=width,
    )
    return hand(btn)


def make_entry(parent, show=None):
    return tk.Entry(
        parent,
        font=(FONT, 11),
        bg=THEME["surface"],
        fg=THEME["text"],
        insertbackground=THEME["text"],
        bd=0,
        relief="flat",
        highlightthickness=1,
        highlightbackground=THEME["line"],
        highlightcolor=THEME["primary"],
        show=show,
    )


def make_text(parent, height=4):
    return tk.Text(
        parent,
        height=height,
        font=(FONT, 11),
        bg=THEME["surface"],
        fg=THEME["text"],
        insertbackground=THEME["text"],
        bd=0,
        relief="flat",
        highlightthickness=1,
        highlightbackground=THEME["line"],
        highlightcolor=THEME["primary"],
        padx=12,
        pady=10,
        wrap="word",
    )


def card(parent, bg=None, padx=18, pady=16):
    return tk.Frame(
        parent,
        bg=bg or THEME["surface"],
        padx=padx,
        pady=pady,
        bd=0,
        relief="flat",
        highlightthickness=0,
    )


class SocialHubUI:
    def __init__(self, root, logic):
        self.root = root
        self.logic = logic

        self.current_user = None
        self.post_image_path = None
        self.post_preview_photo = None

        self.feed_images = {}
        self.chat_images = []
        self.avatar_refs = {}

        self.root.title("SocialHub")
        self.root.geometry("1180x780")
        self.root.minsize(1040, 690)
        self.root.configure(bg=THEME["bg"])

        self.show_login_screen()

    def clear_root(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def render_avatar(self, parent, name, avatar_path="", key=None, size=38, bg=None, side="left"):
        bg = bg or parent.cget("bg")

        if avatar_path and os.path.exists(avatar_path):
            try:
                img = Image.open(avatar_path).resize((size, size))
                photo = ImageTk.PhotoImage(img)
                ref_key = key or f"avatar_{name}_{size}_{len(self.avatar_refs)}"
                self.avatar_refs[ref_key] = photo
                label = tk.Label(parent, image=photo, bg=bg)
                label.pack(side=side, padx=(0, 10), pady=2)
                return label
            except Exception:
                pass

        initial = (name or "?").strip()[:1].upper() or "?"
        label = tk.Label(
            parent,
            text=initial,
            bg=THEME["primary_soft"],
            fg=THEME["primary"],
            font=(FONT, max(10, size // 3), "bold"),
            width=max(2, size // 18),
            padx=6,
            pady=5,
        )
        label.pack(side=side, padx=(0, 10), pady=2)
        return label

    # ================= LOGIN / REGISTER =================
    def show_login_screen(self):
        self.clear_root()
        self.root.configure(bg=THEME["bg"])

        shell = tk.Frame(self.root, bg=THEME["bg"])
        shell.pack(fill="both", expand=True, padx=70, pady=60)

        hero = tk.Frame(shell, bg=THEME["primary"], padx=42, pady=42)
        hero.pack(side="left", fill="both", expand=True)

        tk.Label(hero, text="SocialHub", bg=THEME["primary"], fg="#FFFFFF", font=(FONT, 30, "bold")).pack(anchor="w")
        tk.Label(
            hero,
            text="Mạng xã hội demo có đăng bài, kết bạn, chat và che thông tin nhạy cảm bằng AI.",
            bg=THEME["primary"],
            fg="#DCEBFF",
            font=(FONT, 13),
            justify="left",
            wraplength=390,
        ).pack(anchor="w", pady=(16, 28))

        form = tk.Frame(shell, bg=THEME["surface"], padx=42, pady=42)
        form.pack(side="right", fill="both", padx=(22, 0))

        tk.Label(form, text="Chào mừng trở lại", bg=THEME["surface"], fg=THEME["text"], font=(FONT, 22, "bold")).pack(anchor="w")
        tk.Label(form, text="Đăng nhập để xem bảng tin của bạn", bg=THEME["surface"], fg=THEME["muted"], font=(FONT, 10)).pack(anchor="w", pady=(4, 26))

        tk.Label(form, text="Số điện thoại", bg=THEME["surface"], fg=THEME["text"], font=(FONT, 10, "bold")).pack(anchor="w")
        self.ent_phone = make_entry(form)
        self.ent_phone.pack(fill="x", pady=(7, 16), ipady=9)

        tk.Label(form, text="Mật khẩu", bg=THEME["surface"], fg=THEME["text"], font=(FONT, 10, "bold")).pack(anchor="w")
        self.ent_pwd = make_entry(form, show="*")
        self.ent_pwd.pack(fill="x", pady=(7, 20), ipady=9)

        remembered = self.logic.get_remembered_user()
        if remembered:
            self.ent_phone.insert(0, remembered[0])
            self.ent_pwd.insert(0, remembered[1])

        self.ent_phone.bind("<Return>", lambda _event: self.handle_login())
        self.ent_pwd.bind("<Return>", lambda _event: self.handle_login())

        make_button(form, "Đăng nhập", self.handle_login, "primary").pack(fill="x", pady=(2, 12))
        make_button(form, "Tạo tài khoản mới", self.show_register_screen, "ghost").pack(fill="x")

    def show_register_screen(self):
        self.clear_root()
        self.reg_avatar_path = ""

        wrapper = tk.Frame(self.root, bg=THEME["bg"])
        wrapper.pack(fill="both", expand=True, padx=90, pady=60)

        form = tk.Frame(wrapper, bg=THEME["surface"], padx=42, pady=36)
        form.place(relx=0.5, rely=0.5, anchor="center", width=470)

        tk.Label(form, text="Tạo tài khoản", bg=THEME["surface"], fg=THEME["text"], font=(FONT, 22, "bold")).pack(anchor="w")
        tk.Label(form, text="Tham gia SocialHub để kết nối với bạn bè", bg=THEME["surface"], fg=THEME["muted"], font=(FONT, 10)).pack(anchor="w", pady=(4, 24))

        tk.Label(form, text="Tên hiển thị", bg=THEME["surface"], fg=THEME["text"], font=(FONT, 10, "bold")).pack(anchor="w")
        self.ent_reg_name = make_entry(form)
        self.ent_reg_name.pack(fill="x", pady=(7, 14), ipady=9)

        tk.Label(form, text="Số điện thoại", bg=THEME["surface"], fg=THEME["text"], font=(FONT, 10, "bold")).pack(anchor="w")
        self.ent_reg_phone = make_entry(form)
        self.ent_reg_phone.pack(fill="x", pady=(7, 14), ipady=9)

        tk.Label(form, text="Mật khẩu", bg=THEME["surface"], fg=THEME["text"], font=(FONT, 10, "bold")).pack(anchor="w")
        self.ent_reg_pwd = make_entry(form, show="*")
        self.ent_reg_pwd.pack(fill="x", pady=(7, 14), ipady=9)

        def choose_avatar():
            path = filedialog.askopenfilename(
                title="Chọn ảnh đại diện",
                filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"), ("All files", "*.*")]
            )
            if path:
                self.reg_avatar_path = path
                avatar_label.config(text=os.path.basename(path), fg=THEME["primary"])

        make_button(form, "Chọn ảnh đại diện", choose_avatar, "soft").pack(fill="x", pady=(4, 4))
        avatar_label = tk.Label(form, text="Chưa chọn ảnh", bg=THEME["surface"], fg=THEME["muted"], font=(FONT, 9))
        avatar_label.pack(anchor="center", pady=(0, 14))

        self.ent_reg_name.bind("<Return>", lambda _event: self.ent_reg_phone.focus_set())
        self.ent_reg_phone.bind("<Return>", lambda _event: self.ent_reg_pwd.focus_set())
        self.ent_reg_pwd.bind("<Return>", lambda _event: self.handle_register())

        make_button(form, "Tạo tài khoản", self.handle_register, "primary").pack(fill="x", pady=(0, 12))
        make_button(form, "Quay lại đăng nhập", self.show_login_screen, "ghost").pack(fill="x")

    def handle_login(self):
        phone = self.ent_phone.get().strip()
        password = self.ent_pwd.get().strip()

        user = self.logic.login(phone, password)
        if not user:
            messagebox.showerror("Thất bại", "Số điện thoại hoặc mật khẩu chưa chính xác!")
            return

        self.current_user = user
        self.build_main_ui()

    def handle_register(self):
        name = self.ent_reg_name.get().strip()
        phone = self.ent_reg_phone.get().strip()
        password = self.ent_reg_pwd.get().strip()

        if not name:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên hiển thị!")
            return
        if len(phone) < 10 or len(password) < 8:
            messagebox.showerror("Lỗi", "Số điện thoại hoặc mật khẩu không hợp lệ!")
            return

        ok, msg = self.logic.register(name, phone, password, self.reg_avatar_path)
        if ok:
            messagebox.showinfo("Thành công", msg)
            self.show_login_screen()
        else:
            messagebox.showerror("Lỗi", msg)

    def handle_logout(self):
        self.current_user = None
        self.feed_images.clear()
        self.chat_images.clear()
        self.avatar_refs.clear()
        self.logic.clear_remembered_user()
        self.show_login_screen()

    # ================= MAIN LAYOUT =================
    def build_main_ui(self):
        self.clear_root()
        self.root.configure(bg=THEME["bg"])
        self.post_image_path = None
        self.post_preview_photo = None
        self.post_mask_var = tk.BooleanVar(value=False)

        self.build_header()

        main = tk.Frame(self.root, bg=THEME["bg"])
        main.pack(fill="both", expand=True, padx=20, pady=18)

        self.build_sidebar(main)
        self.build_chat_panel(main)
        self.build_feed(main)

    def build_header(self):
        header = tk.Frame(self.root, bg=THEME["surface"], height=68, padx=20, pady=10)
        header.pack(fill="x")
        header.pack_propagate(False)

        brand = tk.Frame(header, bg=THEME["surface"])
        brand.pack(side="left", fill="y")

        tk.Label(brand, text="S", bg=THEME["primary"], fg="#FFFFFF", font=(FONT, 18, "bold"), width=2).pack(side="left", padx=(0, 10), pady=2)
        tk.Label(brand, text="SocialHub", bg=THEME["surface"], fg=THEME["text"], font=(FONT, 18, "bold")).pack(side="left")

        profile = tk.Frame(header, bg=THEME["surface"])
        profile.pack(side="right")

        self.render_avatar(profile, self.current_user["name"], self.current_user.get("avatar_path", ""), "me", size=36, bg=THEME["surface"])
        tk.Label(profile, text=self.current_user["name"], bg=THEME["surface"], fg=THEME["text"], font=(FONT, 10, "bold")).pack(side="left", padx=(0, 12))
        make_button(profile, "Đăng xuất", self.handle_logout, "danger").pack(side="left")

    def build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=THEME["surface"], width=260, padx=14, pady=16)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="Kết nối", bg=THEME["surface"], fg=THEME["text"], font=(FONT, 15, "bold")).pack(anchor="w")
        tk.Label(sidebar, text="Tìm bạn và mở trò chuyện", bg=THEME["surface"], fg=THEME["muted"], font=(FONT, 9)).pack(anchor="w", pady=(2, 16))

        search_card = card(sidebar, bg=THEME["surface_2"], padx=12, pady=12)
        search_card.pack(fill="x", pady=(0, 16))

        tk.Label(search_card, text="Tìm bằng số điện thoại", bg=THEME["surface_2"], fg=THEME["text"], font=(FONT, 10, "bold")).pack(anchor="w")
        self.ent_search_phone = make_entry(search_card)
        self.ent_search_phone.pack(fill="x", pady=(8, 8), ipady=7)
        self.ent_search_phone.bind("<Return>", lambda _event: self.handle_find_friend())

        make_button(search_card, "Tìm & kết bạn", self.handle_find_friend, "primary").pack(fill="x")

        tk.Label(sidebar, text="Bạn bè", bg=THEME["surface"], fg=THEME["text"], font=(FONT, 12, "bold")).pack(anchor="w", pady=(6, 8))
        self.friend_list_frame = tk.Frame(sidebar, bg=THEME["surface"])
        self.friend_list_frame.pack(fill="both", expand=True)

        self.update_sidebar_friends()

    def build_chat_panel(self, parent):
        self.chat_panel = tk.Frame(parent, bg=THEME["surface"], width=370)
        self.chat_panel.pack(side="right", fill="both", padx=(18, 0))
        self.chat_panel.pack_propagate(False)
        self.render_chat_placeholder()

    def build_feed(self, parent):
        feed_container = tk.Frame(parent, bg=THEME["bg"])
        feed_container.pack(side="left", fill="both", expand=True, padx=(18, 0))

        self.feed_canvas = tk.Canvas(feed_container, bg=THEME["bg"], highlightthickness=0)
        self.feed_canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(feed_container, orient="vertical", command=self.feed_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.feed_canvas.configure(yscrollcommand=scrollbar.set)

        self.feed_frame = tk.Frame(self.feed_canvas, bg=THEME["bg"])
        self.feed_window = self.feed_canvas.create_window((0, 0), window=self.feed_frame, anchor="nw")

        self.feed_frame.bind("<Configure>", lambda _event: self.feed_canvas.configure(scrollregion=self.feed_canvas.bbox("all")))
        self.feed_canvas.bind("<Configure>", lambda event: self.feed_canvas.itemconfig(self.feed_window, width=event.width))

        self.create_post_box()
        self.load_feed()

    def render_chat_placeholder(self):
        for child in self.chat_panel.winfo_children():
            child.destroy()

        box = tk.Frame(self.chat_panel, bg=THEME["surface"], padx=26, pady=26)
        box.pack(fill="both", expand=True)

        tk.Label(box, text="💬", bg=THEME["surface"], fg=THEME["primary"], font=(FONT, 44)).pack(pady=(130, 8))
        tk.Label(box, text="Chưa mở cuộc trò chuyện", bg=THEME["surface"], fg=THEME["text"], font=(FONT, 15, "bold")).pack()
        tk.Label(box, text="Chọn một người bạn bên trái để bắt đầu nhắn tin", bg=THEME["surface"], fg=THEME["muted"], font=(FONT, 10), wraplength=250, justify="center").pack(pady=(8, 0))

    # ================= FRIEND =================
    def handle_find_friend(self):
        phone = self.ent_search_phone.get().strip()
        if not phone:
            return

        if phone == self.current_user["phone"]:
            messagebox.showwarning("Không hợp lệ", "Bạn không thể tự kết bạn với chính mình!")
            return

        friend = self.logic.find_user_by_phone(phone)
        if not friend:
            messagebox.showerror("Không tìm thấy", "Không có người dùng nào sử dụng số điện thoại này!")
            return

        if self.logic.are_friends(self.current_user["phone"], phone):
            messagebox.showinfo("Thông báo", f"Bạn và {friend['name']} đã là bạn bè.")
            return

        confirm = messagebox.askyesno(
            "Xác nhận kết bạn",
            f"Tìm thấy người dùng:\n\nTên: {friend['name']}\nSĐT: {friend['phone']}\n\nBạn có muốn kết bạn không?"
        )
        if not confirm:
            return

        ok, msg = self.logic.add_friend(self.current_user["phone"], phone)
        if ok:
            self.ent_search_phone.delete(0, "end")
            self.update_sidebar_friends()
            messagebox.showinfo("Thành công", msg)
        else:
            messagebox.showwarning("Thông báo", msg)

    def update_sidebar_friends(self):
        for child in self.friend_list_frame.winfo_children():
            child.destroy()

        friends = self.logic.get_friends(self.current_user["phone"])
        if not friends:
            empty = tk.Frame(self.friend_list_frame, bg=THEME["surface_2"], padx=12, pady=14)
            empty.pack(fill="x", pady=8)
            tk.Label(empty, text="Chưa có bạn bè", bg=THEME["surface_2"], fg=THEME["text"], font=(FONT, 10, "bold")).pack(anchor="w")
            tk.Label(empty, text="Hãy tìm bằng số điện thoại ở trên", bg=THEME["surface_2"], fg=THEME["muted"], font=(FONT, 9)).pack(anchor="w", pady=(4, 0))
            return

        for friend in friends:
            row = tk.Frame(self.friend_list_frame, bg=THEME["surface_2"], padx=10, pady=10)
            row.pack(fill="x", pady=5)

            self.render_avatar(row, friend["name"], friend.get("avatar_path", ""), f"friend_{friend['phone']}", size=32, bg=THEME["surface_2"])
            btn = tk.Button(
                row,
                text=friend["name"],
                bg=THEME["surface_2"],
                fg=THEME["text"],
                activebackground=THEME["primary_soft"],
                font=(FONT, 10, "bold"),
                anchor="w",
                bd=0,
                relief="flat",
                command=lambda f=friend: self.open_chat(f),
            )
            hand(btn)
            btn.pack(side="left", fill="x", expand=True)

    # ================= POST =================
    def create_post_box(self):
        box = card(self.feed_frame, padx=18, pady=16)
        box.pack(fill="x", pady=(0, 16), padx=2)

        head = tk.Frame(box, bg=THEME["surface"])
        head.pack(fill="x")

        self.render_avatar(head, self.current_user["name"], self.current_user.get("avatar_path", ""), "post_me", size=38, bg=THEME["surface"])
        tk.Label(head, text=f"Bạn đang nghĩ gì, {self.current_user['name']}?", bg=THEME["surface"], fg=THEME["muted"], font=(FONT, 11)).pack(side="left", fill="x", expand=True, pady=7)

        self.post_text = make_text(box, height=4)
        self.post_text.pack(fill="x", pady=(14, 10))

        self.post_preview_frame = tk.Frame(box, bg=THEME["surface_2"], padx=12, pady=12)
        self.post_preview_label = tk.Label(self.post_preview_frame, bg=THEME["surface_2"])
        self.post_preview_label.pack(side="left", padx=(0, 10))
        self.post_preview_name = tk.Label(self.post_preview_frame, text="", bg=THEME["surface_2"], fg=THEME["text"], font=(FONT, 9, "bold"))
        self.post_preview_name.pack(side="left", fill="x", expand=True)
        make_button(self.post_preview_frame, " Bỏ dữ liệu", self.remove_post_image, "danger").pack(side="right")
        self.post_preview_frame.pack_forget()

        action_row = tk.Frame(box, bg=THEME["surface"])
        action_row.pack(fill="x", pady=(2, 0))

        make_button(action_row, "🖼  Thêm dữ liệu", self.choose_post_image, "soft").pack(side="left")

        tk.Checkbutton(
            action_row,
            text="Che dữ liệu",
            variable=self.post_mask_var,
            bg=THEME["surface"],
            fg=THEME["text"],
            activebackground=THEME["surface"],
            font=(FONT, 10),
            selectcolor=THEME["surface"],
        ).pack(side="left", padx=12)

        make_button(action_row, "Đăng bài", self.publish_post, "primary").pack(side="right")

    def choose_post_image(self):
        # Bỏ 'pdf' ra khỏi danh sách
        path = filedialog.askopenfilename(
            title="Chọn tài liệu",
            filetypes=[("Tài liệu/Ảnh", "*.png *.jpg *.jpeg *.docx *.doc"), ("Hình ảnh", "*.png *.jpg *.jpeg *.bmp *.webp")]
        )
        if path:
            self.post_image_path = path
            ext = path.lower().split('.')[-1]
            
            # Chỉ hiển thị tài liệu nếu là Word
            if ext in ['doc', 'docx']:
                self.post_preview_photo = None
                self.post_preview_label.config(image="", text="📄 [Tài liệu Word]", fg=THEME["primary"])
            else:
                # Xử lý hiển thị Thumbnail cho ảnh như cũ
                try:
                    img = Image.open(path)
                    img.thumbnail((96, 96))
                    self.post_preview_photo = ImageTk.PhotoImage(img)
                    self.post_preview_label.config(image=self.post_preview_photo, text="")
                except Exception: pass
            
            self.post_preview_name.config(text=os.path.basename(path))
            self.post_preview_frame.pack(fill="x", pady=(0, 10))

    def remove_post_image(self):
        self.post_image_path = None
        self.post_preview_photo = None
        self.post_preview_label.config(image="")
        self.post_preview_name.config(text="")
        self.post_preview_frame.pack_forget()

    def publish_post(self):
        content = self.post_text.get("1.0", "end").strip()

        ok, msg = self.logic.create_post(
            self.current_user,
            content,
            image_path=self.post_image_path,
            mask_enabled=self.post_mask_var.get(),
            parent_ui=self.root,
        )

        if ok:
            self.post_text.delete("1.0", "end")
            self.remove_post_image()
            self.post_mask_var.set(False)
            self.load_feed()

            if msg and msg not in ("Đã đăng bài.", "Đã xử lý ảnh bằng test1.py."):
                messagebox.showinfo("Thông báo", msg)
        else:
            messagebox.showwarning("Thông báo", msg)

    def load_feed(self):
        children = self.feed_frame.winfo_children()
        for child in children[1:]:
            child.destroy()

        posts = self.logic.get_feed_posts(self.current_user["phone"])
        if not posts:
            empty = card(self.feed_frame, bg=THEME["surface"], padx=24, pady=28)
            empty.pack(fill="x", pady=(0, 12), padx=2)
            tk.Label(empty, text="🌱", bg=THEME["surface"], fg=THEME["primary"], font=(FONT, 28)).pack()
            tk.Label(empty, text="Bảng tin đang trống", bg=THEME["surface"], fg=THEME["text"], font=(FONT, 14, "bold")).pack(pady=(4, 4))
            tk.Label(empty, text="Hãy đăng bài đầu tiên hoặc kết bạn để xem bài viết của họ.", bg=THEME["surface"], fg=THEME["muted"], font=(FONT, 10)).pack()
            return

        for post in posts:
            self.render_post(post)

    def render_post(self, post):
        p_frame = card(self.feed_frame, padx=18, pady=16)
        p_frame.pack(fill="x", pady=(0, 14), padx=2)

        top = tk.Frame(p_frame, bg=THEME["surface"])
        top.pack(fill="x")

        self.render_avatar(top, post["author_name"], post.get("avatar_path", ""), f"post_{post['id']}", size=38, bg=THEME["surface"])

        info = tk.Frame(top, bg=THEME["surface"])
        info.pack(side="left", fill="x", expand=True)

        tk.Label(info, text=post["author_name"], bg=THEME["surface"], fg=THEME["text"], font=(FONT, 11, "bold")).pack(anchor="w")
        tk.Label(info, text=post["timestamp"] or "Vừa xong", bg=THEME["surface"], fg=THEME["muted"], font=(FONT, 9)).pack(anchor="w")

        if post["author_phone"] == self.current_user["phone"]:
            menu = tk.Frame(top, bg=THEME["surface"])
            menu.pack(side="right")
            make_button(menu, "Sửa", lambda p=post: self.edit_post(p), "soft").pack(side="left", padx=(0, 6))
            make_button(menu, "Xóa", lambda p=post: self.delete_post(p), "danger").pack(side="left")

        if post["content"]:
            tk.Label(
                p_frame,
                text=post["content"],
                bg=THEME["surface"],
                fg=THEME["text"],
                font=(FONT, 11),
                wraplength=650,
                justify="left",
            ).pack(anchor="w", fill="x", pady=(14, 10))

        # ==========================================
        # XỬ LÝ ĐÍNH KÈM (ẢNH HOẶC FILE WORD)
        # ==========================================
        if post["image_path"] and os.path.exists(post["image_path"]):
            ext = post["image_path"].lower().split('.')[-1]
            
            # ==========================================
        if post["image_path"] and os.path.exists(post["image_path"]):
            ext = post["image_path"].lower().split('.')[-1]
            
            if ext in ['doc', 'docx', 'pdf']:
                file_name = os.path.basename(post["image_path"])
                doc_box = tk.Frame(p_frame, bg=THEME["surface_2"], padx=15, pady=12)
                doc_box.pack(anchor="w", fill="x", pady=(2, 10))
                
                # Biến Label thành một đường link có thể click
                link_label = tk.Label(
                    doc_box, 
                    text=f"📄 Tài liệu: {file_name}", 
                    bg=THEME["surface_2"], 
                    fg=THEME["primary"], 
                    font=(FONT, 10, "bold", "underline"), # Gạch chân cho giống link
                    cursor="hand2" # Đổi con trỏ chuột thành hình bàn tay
                )
                link_label.pack(anchor="w")
                
                # Gán sự kiện click chuột trái để mở file
                link_label.bind("<Button-1>", lambda e, path=post["image_path"]: open_document(path))
                
                tk.Label(doc_box, text="(Văn bản đã được AI quét và che thông tin)", bg=THEME["surface_2"], fg=THEME["muted"], font=(FONT, 9, "italic")).pack(anchor="w", pady=(2, 0))
            else:
                # Giao diện hiển thị Hình ảnh như cũ
                try:
                    img = Image.open(post["image_path"])
                    img.thumbnail((620, 420))
                    photo = ImageTk.PhotoImage(img)
                    self.feed_images[f"p_{post['id']}"] = photo

                    image_box = tk.Frame(p_frame, bg=THEME["surface_2"], padx=10, pady=10)
                    image_box.pack(anchor="w", fill="x", pady=(2, 10))
                    tk.Label(image_box, image=photo, bg=THEME["surface_2"]).pack(anchor="center")
                except Exception:
                    pass

        if post.get("mask_enabled"):
            tk.Label(
                p_frame,
                text="🛡 Dữ liệu đã được xử lý che thông tin nhạy cảm",
                bg=THEME["surface"],
                fg=THEME["muted"],
                font=(FONT, 9, "italic"),
            ).pack(anchor="w", pady=(0, 8))

        comments = self.logic.get_comments(post["id"])
        if comments:
            cmt_box = tk.Frame(p_frame, bg=THEME["surface_2"], padx=12, pady=8)
            cmt_box.pack(fill="x", pady=(4, 8))
            for cmt in comments[-3:]:
                tk.Label(
                    cmt_box,
                    text=f"{cmt['author_name']}: {cmt['content']}",
                    bg=THEME["surface_2"],
                    fg=THEME["text"],
                    font=(FONT, 9),
                    anchor="w",
                    justify="left",
                    wraplength=620,
                ).pack(fill="x", anchor="w", pady=2)

        actions = tk.Frame(p_frame, bg=THEME["surface"])
        actions.pack(fill="x", pady=(6, 0))

        make_button(actions, f"♡ Thích ({post['likes']})", lambda p=post: self.like_post(p), "soft").pack(side="left", padx=(0, 8))
        make_button(actions, "💬 Bình luận", lambda p=post: self.comment_post(p), "soft").pack(side="left", padx=(0, 8))

    def like_post(self, post):
        self.logic.like_post(post["id"])
        self.load_feed()

    def comment_post(self, post):
        content = simpledialog.askstring("Bình luận", "Nhập nội dung bình luận:", parent=self.root)
        if content and content.strip():
            self.logic.add_comment(post["id"], self.current_user, content.strip())
            self.load_feed()

    def edit_post(self, post):
        content = simpledialog.askstring("Sửa bài viết", "Nhập nội dung mới:", initialvalue=post["content"], parent=self.root)
        if content is not None and content.strip():
            self.logic.edit_post(post["id"], content.strip())
            self.load_feed()

    def delete_post(self, post):
        confirm = messagebox.askyesno("Xóa bài viết", "Bạn có chắc chắn muốn xóa bài viết này?")
        if confirm:
            self.logic.delete_post(post["id"])
            self.load_feed()

    # ================= CHAT =================
    def open_chat(self, friend):
        for child in self.chat_panel.winfo_children():
            child.destroy()

        ChatPanel(
            parent=self.chat_panel,
            logic=self.logic,
            current_user=self.current_user,
            partner=friend,
            image_store=self.chat_images,
            avatar_renderer=self.render_avatar,
        )


class ChatPanel:
    def __init__(self, parent, logic, current_user, partner, image_store, avatar_renderer):
        self.window = parent
        self.logic = logic
        self.current_user = current_user
        self.partner = partner
        self.image_store = image_store
        self.avatar_renderer = avatar_renderer

        self.selected_image_path = None
        self.preview_photo = None
        self.mask_var = tk.BooleanVar(value=False)
        self.last_msg_count = -1

        self.build_ui()
        self.load_chat_history(force=True)
        self.start_auto_refresh()

    def build_ui(self):
        header = tk.Frame(self.window, bg=THEME["surface"], height=64, padx=14, pady=10)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        self.avatar_renderer(header, self.partner["name"], self.partner.get("avatar_path", ""), f"chat_{self.partner['phone']}", size=36, bg=THEME["surface"])

        info = tk.Frame(header, bg=THEME["surface"])
        info.pack(side="left", fill="x", expand=True)

        tk.Label(info, text=self.partner["name"], bg=THEME["surface"], fg=THEME["text"], font=(FONT, 12, "bold")).pack(anchor="w")
        tk.Label(info, text="● Đang hoạt động", bg=THEME["surface"], fg=THEME["success"], font=(FONT, 9)).pack(anchor="w")

        bottom = tk.Frame(self.window, bg=THEME["surface"], pady=10, padx=12)
        bottom.pack(fill="x", side="bottom")

        self.preview_frame = tk.Frame(bottom, bg=THEME["surface_2"], padx=10, pady=10)
        self.preview_label = tk.Label(self.preview_frame, bg=THEME["surface_2"])
        self.preview_label.pack(side="left", padx=(0, 8))

        self.preview_name = tk.Label(self.preview_frame, text="", bg=THEME["surface_2"], fg=THEME["text"], font=(FONT, 9, "bold"))
        self.preview_name.pack(side="left", fill="x", expand=True)

        tk.Checkbutton(
            self.preview_frame,
            text="Che ảnh bằng AI",
            variable=self.mask_var,
            bg=THEME["surface_2"],
            fg=THEME["text"],
            selectcolor=THEME["surface_2"],
        ).pack(side="left", padx=5)

        make_button(self.preview_frame, "Bỏ", self.remove_image, "danger").pack(side="right")

        input_row = tk.Frame(bottom, bg=THEME["surface"])
        input_row.pack(fill="x", pady=(4, 0))

        # Đúng thứ tự: ô nhắn tin -> nút gửi -> nút ảnh nhỏ
        self.entry = make_entry(input_row)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=9)
        self.entry.bind("<Return>", lambda _event: self.send_message())

        make_button(input_row, "Gửi", self.send_message, "primary", width=6).pack(side="left", padx=(0, 6))
        make_button(input_row, "📎", self.choose_image, "soft", width=3).pack(side="left")

        chat_container = tk.Frame(self.window, bg=THEME["bg"])
        chat_container.pack(fill="both", expand=True, side="top")

        self.canvas = tk.Canvas(chat_container, bg=THEME["bg"], highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(chat_container, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")

        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.chat_frame = tk.Frame(self.canvas, bg=THEME["bg"])
        self.chat_window_obj = self.canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")

        self.chat_frame.bind("<Configure>", lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfig(self.chat_window_obj, width=event.width))

    def choose_image(self):
        path = filedialog.askopenfilename(
            title="Chọn tài liệu gửi",
            filetypes=[
                ("Tất cả tài liệu", "*.png *.jpg *.jpeg *.bmp *.webp *.pdf *.doc *.docx"),
                ("Hình ảnh", "*.png *.jpg *.jpeg *.bmp *.webp"), 
                ("Tài liệu (PDF/Word)", "*.pdf *.doc *.docx")
            ]
        )
        if path:
            self.selected_image_path = path
            ext = path.lower().split('.')[-1]

            if ext in ['pdf', 'doc', 'docx']:
                self.preview_photo = None
                self.preview_label.config(image="", text="📄", fg=THEME["primary"], font=(FONT, 20))
            else:
                try:
                    img = Image.open(path)
                    img.thumbnail((68, 68))
                    self.preview_photo = ImageTk.PhotoImage(img)
                    self.preview_label.config(image=self.preview_photo, text="")
                except Exception:
                    pass

            self.preview_name.config(text=os.path.basename(path))
            self.preview_frame.pack(fill="x", pady=(0, 8))

    def remove_image(self):
        self.selected_image_path = None
        self.preview_photo = None
        self.preview_label.config(image="")
        self.preview_name.config(text="")
        self.mask_var.set(False)
        self.preview_frame.pack_forget()

    def load_chat_history(self, force=False):
        logs = self.logic.get_chat_history(self.current_user["phone"], self.partner["phone"])

        if not force and len(logs) == self.last_msg_count:
            return

        self.last_msg_count = len(logs)

        for child in self.chat_frame.winfo_children():
            child.destroy()

        if not logs:
            empty = tk.Frame(self.chat_frame, bg=THEME["bg"], padx=20, pady=80)
            empty.pack(fill="both", expand=True)

            tk.Label(empty, text="Bắt đầu cuộc trò chuyện", bg=THEME["bg"], fg=THEME["text"], font=(FONT, 13, "bold")).pack()
            tk.Label(empty, text="Gửi lời chào hoặc một tấm ảnh cho bạn bè.", bg=THEME["bg"], fg=THEME["muted"], font=(FONT, 10)).pack(pady=(6, 0))

        for msg in logs:
            is_me = msg["sender_phone"] == self.current_user["phone"]
            align = "e" if is_me else "w"

            outer = tk.Frame(self.chat_frame, bg=THEME["bg"])
            outer.pack(fill="x", padx=12, pady=5)

            bubble_bg = THEME["bubble_me"] if is_me else THEME["bubble_other"]
            bubble_fg = "#FFFFFF" if is_me else THEME["text"]

            bubble = tk.Frame(outer, bg=bubble_bg, padx=12, pady=9)
            bubble.pack(anchor=align)

            if msg["content"]:
                tk.Label(
                    bubble,
                    text=msg["content"],
                    bg=bubble_bg,
                    fg=bubble_fg,
                    wraplength=230,
                    justify="left",
                    font=(FONT, 10),
                    padx=2,
                    pady=2,
                ).pack(anchor="w")

            # ==========================================
            # XỬ LÝ ĐÍNH KÈM TRONG CHAT
            # ==========================================
            if msg["image_path"] and os.path.exists(msg["image_path"]):
                ext = msg["image_path"].lower().split('.')[-1]
                
                if ext in ['doc', 'docx', 'pdf']:
                    file_name = os.path.basename(msg["image_path"])
                    
                    # Tạo Label giống link trong bong bóng chat
                    link_label = tk.Label(
                        bubble,
                        text=f"📄 {file_name}",
                        bg=bubble_bg,
                        fg=bubble_fg,
                        font=(FONT, 10, "bold", "underline"),
                        cursor="hand2",
                        wraplength=220,
                        justify="left"
                    )
                    link_label.pack(anchor="w", pady=(5, 0))
                    
                    # Gán sự kiện click chuột
                    link_label.bind("<Button-1>", lambda e, path=msg["image_path"]: open_document(path))
                    
                else:
                    try:
                        img = Image.open(msg["image_path"])
                        img.thumbnail((220, 220))
                        photo = ImageTk.PhotoImage(img)
                        self.image_store.append(photo)

                        tk.Label(bubble, image=photo, bg=bubble_bg).pack(anchor="w", pady=(5, 0))
                    except Exception:
                        pass

        self.window.after(50, lambda: self.canvas.yview_moveto(1.0))

    def send_message(self):
        text = self.entry.get().strip()

        ok, msg = self.logic.send_message(
            self.current_user["phone"],
            self.partner["phone"],
            content=text,
            image_path=self.selected_image_path,
            mask_enabled=self.mask_var.get(),
            parent_ui=self.window.winfo_toplevel(),
        )

        if ok:
            self.entry.delete(0, "end")
            self.remove_image()
            self.load_chat_history(force=True)

            if msg and msg not in ("Đã gửi tin nhắn.", "Đã xử lý ảnh bằng test1.py."):
                messagebox.showinfo("Thông báo", msg)
        else:
            messagebox.showwarning("Thông báo", msg)

    def start_auto_refresh(self):
        if self.window.winfo_exists():
            self.load_chat_history()
            self.window.after(1000, self.start_auto_refresh)
