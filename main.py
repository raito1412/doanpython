import tkinter as tk

from socialhub_logic import init_db, SocialAppLogic
from socialhub_ui import SocialHubUI


def main():
    """
    main.py chỉ connect:
    - khởi tạo database
    - tạo logic layer, trong đó AI redact connect tới test1_redaction_logic.py
    - tạo UI layer
    - chạy Tkinter
    """
    init_db()
    logic = SocialAppLogic()

    root = tk.Tk()
    SocialHubUI(root, logic)
    root.mainloop()


if __name__ == "__main__":
    main()
