import tkinter as tk
import traceback

from gui.main_window import MainWindow


def main():
    try:

        root = tk.Tk()

        application = MainWindow(root)

        root.mainloop()

    except Exception:

        print()
        print("--- APPLICATION ERROR ---")
        print(traceback.format_exc())
        print("-------------------------")
        print()

        input("Press Enter to continue...")


if __name__ == "__main__":
    main()