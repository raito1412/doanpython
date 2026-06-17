import os
import sqlite3
from datetime import datetime

DB_NAME = "social_app.db"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROCESSED_IMG_DIR = os.path.join(BASE_DIR, "processed_images")
os.makedirs(PROCESSED_IMG_DIR, exist_ok=True)


# ================= DATABASE =================
def safe_add_column(cursor, table_name, column_name, column_type):
    try:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
    except sqlite3.OperationalError:
        # Cột đã tồn tại thì bỏ qua.
        pass


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

    safe_add_column(cursor, "users", "avatar_path", "TEXT")
    safe_add_column(cursor, "comments", "author_phone", "TEXT")
    safe_add_column(cursor, "comments", "timestamp", "TEXT")
    safe_add_column(cursor, "posts", "mask_enabled", "INTEGER DEFAULT 0")
    safe_add_column(cursor, "messages", "mask_enabled", "INTEGER DEFAULT 0")

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


# ================= IMAGE REDACTION CONNECTOR =================
def _load_test1_module():
    """
    Load file test1_redaction_logic.py để dùng lại logic che ảnh gốc.
    File này không viết lại logic che, chỉ import và gọi hàm process_and_redact().
    """
    import importlib.util

    script_candidates = [
        os.path.join(BASE_DIR, "test1_redaction_logic.py"),
        os.path.join(BASE_DIR, "test1_redaction_logic(3).py"),  # hỗ trợ tên file khi tải từ ChatGPT
    ]

    script_path = next((path for path in script_candidates if os.path.exists(path)), None)
    if not script_path:
        raise FileNotFoundError("Thiếu file test1_redaction_logic.py.")

    spec = importlib.util.spec_from_file_location("test1_redaction_logic", script_path)
    if spec is None or spec.loader is None:
        raise ImportError("Không thể load test1_redaction_logic.py.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "process_and_redact"):
        raise AttributeError("test1_redaction_logic.py thiếu hàm process_and_redact(image_path, output_path, parent_window).")

    return module


def run_test1_redaction(image_path, output_path, parent_ui=None):
    """
    Cầu nối duy nhất giữa UI và test1_redaction_logic.py.

    Luồng chạy:
    UI chọn ảnh + tick che AI
        -> socialhub_logic.run_test1_redaction()
        -> test1_redaction_logic.process_and_redact()
        -> lưu ảnh đã che vào output_path

    Không viết lại OCR, không viết lại vùng che, không sửa giao diện.
    """
    if not image_path or not os.path.exists(image_path):
        return False, image_path, "Không tìm thấy ảnh."

    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        test1_module = _load_test1_module()
        success = test1_module.process_and_redact(image_path, output_path, parent_ui)

        if not success:
            return False, image_path, "Đã hủy hoặc xử lý ảnh thất bại."

        if not os.path.exists(output_path):
            return False, image_path, "test1_redaction_logic.py chưa tạo ảnh output."

        return True, output_path, "Đã xử lý ảnh bằng test1.py."

    except Exception as exc:
        return False, image_path, f"Lỗi khi gọi test1_redaction_logic.py: {exc}"


def process_image(image_path, output_path, parent_ui=None):
    """Alias để UI/logic khác có thể gọi ngắn gọn."""
    return run_test1_redaction(image_path, output_path, parent_ui)

class SocialAppLogic:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name

    def _connect(self):
        return sqlite3.connect(self.db_name)

    # ================= AUTH =================
    def get_remembered_user(self):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT phone, password FROM remember_me WHERE id=1")
        row = cursor.fetchone()
        conn.close()
        return row

    def remember_user(self, phone, password):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM remember_me")
        cursor.execute("INSERT INTO remember_me (id, phone, password) VALUES (1, ?, ?)", (phone, password))
        conn.commit()
        conn.close()

    def clear_remembered_user(self):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM remember_me")
        conn.commit()
        conn.close()

    def login(self, phone, password):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT phone, password, name, avatar_path FROM users WHERE phone=? AND password=?",
            (phone, password),
        )
        user = cursor.fetchone()
        conn.close()

        if not user:
            return None

        self.remember_user(phone, password)
        return {
            "phone": user[0],
            "password": user[1],
            "name": user[2],
            "avatar_path": user[3] or "",
        }

    def register(self, name, phone, password, avatar_path=""):
        if not name:
            return False, "Vui lòng nhập tên hiển thị."
        if not phone or len(phone) < 10:
            return False, "Số điện thoại không hợp lệ."
        if not password or len(password) < 8:
            return False, "Mật khẩu phải có ít nhất 8 ký tự."

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT phone FROM users WHERE phone=?", (phone,))
        if cursor.fetchone():
            conn.close()
            return False, "Số điện thoại này đã tồn tại!"

        try:
            cursor.execute(
                "INSERT INTO users (phone, password, name, avatar_path) VALUES (?, ?, ?, ?)",
                (phone, password, name, avatar_path or ""),
            )
            conn.commit()
            return True, "Đăng ký thành công!"
        except sqlite3.Error as exc:
            return False, f"Không thể tạo tài khoản: {exc}"
        finally:
            conn.close()

    # ================= FRIEND =================
    def find_user_by_phone(self, phone):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT phone, name, avatar_path FROM users WHERE phone=?", (phone,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {"phone": row[0], "name": row[1], "avatar_path": row[2] or ""}

    def are_friends(self, my_phone, friend_phone):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM friends WHERE user_phone=? AND friend_phone=?",
            (my_phone, friend_phone),
        )
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def add_friend(self, my_phone, friend_phone):
        if not friend_phone:
            return False, "Vui lòng nhập số điện thoại."

        if friend_phone == my_phone:
            return False, "Bạn không thể tự kết bạn với chính mình!"

        friend = self.find_user_by_phone(friend_phone)
        if not friend:
            return False, "Không có người dùng nào sử dụng số điện thoại này!"

        if self.are_friends(my_phone, friend_phone):
            return False, f"Bạn và {friend['name']} đã là bạn bè."

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO friends (user_phone, friend_phone) VALUES (?, ?)",
            (my_phone, friend_phone),
        )
        cursor.execute(
            "INSERT OR IGNORE INTO friends (user_phone, friend_phone) VALUES (?, ?)",
            (friend_phone, my_phone),
        )
        conn.commit()
        conn.close()

        return True, f"Đã kết bạn với {friend['name']}!"

    def get_friends(self, my_phone):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT users.name, users.phone, users.avatar_path
            FROM friends
            JOIN users ON friends.friend_phone = users.phone
            WHERE friends.user_phone = ?
            ORDER BY users.name
            """,
            (my_phone,),
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            {"name": name, "phone": phone, "avatar_path": avatar_path or ""}
            for name, phone, avatar_path in rows
        ]

    # ================= POST =================
    def create_post(self, current_user, content, image_path=None, mask_enabled=False, parent_ui=None):
        if not content and not image_path:
            return False, "Bài viết cần có nội dung hoặc hình ảnh."

        final_image_path = image_path or ""
        mask_val = 1 if mask_enabled else 0
        info_message = ""

        if mask_val == 1 and image_path:
            filename = f"redact_post_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
            output_path = os.path.join(PROCESSED_IMG_DIR, filename)
            ok, result_path, msg = run_test1_redaction(image_path, output_path, parent_ui)
            if not ok:
                return False, msg
            final_image_path = result_path
            info_message = msg

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO posts (author_phone, author_name, content, image_path, mask_enabled, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                current_user["phone"],
                current_user["name"],
                content,
                final_image_path,
                mask_val,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
        )
        conn.commit()
        conn.close()

        return True, info_message or "Đã đăng bài."

    def get_feed_posts(self, my_phone):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.id, p.author_phone, p.author_name, p.content,
                   p.image_path, p.mask_enabled, p.likes, p.timestamp,
                   u.avatar_path
            FROM posts AS p
            LEFT JOIN users AS u ON p.author_phone = u.phone
            WHERE p.author_phone = ?
               OR p.author_phone IN (
                    SELECT friend_phone FROM friends WHERE user_phone = ?
               )
            ORDER BY p.id DESC
            """,
            (my_phone, my_phone),
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": r[0],
                "author_phone": r[1],
                "author_name": r[2],
                "content": r[3] or "",
                "image_path": r[4] or "",
                "mask_enabled": bool(r[5]),
                "likes": r[6] or 0,
                "timestamp": r[7] or "",
                "avatar_path": r[8] or "",
            }
            for r in rows
        ]

    def like_post(self, post_id):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE posts SET likes = likes + 1 WHERE id=?", (post_id,))
        conn.commit()
        conn.close()

    def edit_post(self, post_id, new_content):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE posts SET content=?, timestamp=? WHERE id=?",
            (new_content, datetime.now().strftime("%Y-%m-%d %H:%M"), post_id),
        )
        conn.commit()
        conn.close()

    def delete_post(self, post_id):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM comments WHERE post_id=?", (post_id,))
        cursor.execute("DELETE FROM posts WHERE id=?", (post_id,))
        conn.commit()
        conn.close()

    def get_comments(self, post_id):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT author_name, content, timestamp FROM comments WHERE post_id=? ORDER BY id ASC",
            (post_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            {"author_name": row[0], "content": row[1], "timestamp": row[2] or ""}
            for row in rows
        ]

    def add_comment(self, post_id, current_user, content):
        if not content:
            return False, "Bình luận trống."

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO comments (post_id, author_phone, author_name, content, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                post_id,
                current_user["phone"],
                current_user["name"],
                content,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
        )
        conn.commit()
        conn.close()
        return True, "Đã bình luận."

    # ================= CHAT =================
    def get_chat_history(self, my_phone, partner_phone):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT sender_phone, content, image_path, mask_enabled, timestamp
            FROM messages
            WHERE (sender_phone=? AND receiver_phone=?)
               OR (sender_phone=? AND receiver_phone=?)
            ORDER BY id ASC
            """,
            (my_phone, partner_phone, partner_phone, my_phone),
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "sender_phone": row[0],
                "content": row[1] or "",
                "image_path": row[2] or "",
                "mask_enabled": bool(row[3]),
                "timestamp": row[4] or "",
            }
            for row in rows
        ]

    def send_message(self, my_phone, partner_phone, content="", image_path=None, mask_enabled=False, parent_ui=None):
        if not content and not image_path:
            return False, "Tin nhắn trống."

        final_image_path = image_path or ""
        mask_val = 1 if mask_enabled else 0
        info_message = ""

        if mask_val == 1 and image_path:
            filename = f"redact_chat_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
            output_path = os.path.join(PROCESSED_IMG_DIR, filename)
            ok, result_path, msg = run_test1_redaction(image_path, output_path, parent_ui)
            if not ok:
                return False, msg
            final_image_path = result_path
            info_message = msg

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO messages (sender_phone, receiver_phone, content, image_path, mask_enabled, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                my_phone,
                partner_phone,
                content,
                final_image_path,
                mask_val,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        conn.close()

        return True, info_message or "Đã gửi tin nhắn."
