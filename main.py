import tkinter as tk
import traceback

from gui.main_window import MainWindow

try:
    import sv_ttk
except ImportError:
    sv_ttk = None


def main():
    try:

        root = tk.Tk()

        if sv_ttk is not None:
            # Falls back to Tk's plain default theme if sv-ttk isn't
            # installed (e.g. setup.bat hasn't been re-run yet) -
            # cosmetic only, never a reason for the app not to start.
            sv_ttk.set_theme("light", root)

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