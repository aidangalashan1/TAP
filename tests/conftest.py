# tests/conftest.py

import sys
import types


def _install_tkinter_stub():
    """
    A handful of tests exercise pure logic inside gui/ modules (e.g.
    RuleWizardDialog's condition-building logic) without ever opening
    a real window. Those modules import tkinter at module load time,
    which isn't installed in every environment this suite runs in
    (including the one this was developed in).

    If real tkinter is importable, this does nothing - the real
    thing is always preferred. Otherwise, install a minimal stand-in
    with just enough surface (StringVar/BooleanVar with get/set,
    inert widget classes, messagebox no-ops) for those modules to
    import and for their non-widget logic to run under test.
    """

    try:
        import tkinter  # noqa: F401
        return
    except ImportError:
        pass

    if "tkinter" in sys.modules:
        return

    tk_module = types.ModuleType("tkinter")

    class _StubVar:
        def __init__(self, value=""):
            self._value = value

        def get(self):
            return self._value

        def set(self, value):
            self._value = value

    class _StubWidget:
        def __init__(self, *args, **kwargs):
            pass

        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    tk_module.StringVar = _StubVar
    tk_module.BooleanVar = _StubVar
    tk_module.Toplevel = _StubWidget
    tk_module.Listbox = _StubWidget
    tk_module.Text = _StubWidget
    tk_module.END = "end"
    tk_module.EXTENDED = "extended"
    tk_module.LEFT = "left"
    tk_module.RIGHT = "right"
    tk_module.BOTH = "both"
    tk_module.X = "x"
    tk_module.Y = "y"

    messagebox_module = types.ModuleType("tkinter.messagebox")
    messagebox_module.showwarning = lambda *a, **k: None
    messagebox_module.showinfo = lambda *a, **k: None
    messagebox_module.showerror = lambda *a, **k: None
    messagebox_module.askyesno = lambda *a, **k: True

    simpledialog_module = types.ModuleType("tkinter.simpledialog")
    simpledialog_module.askstring = lambda *a, **k: None

    ttk_module = types.ModuleType("tkinter.ttk")

    class _StubTTKWidget(_StubWidget):
        pass

    for widget_name in (
        "Frame",
        "Label",
        "Button",
        "Combobox",
        "Entry",
        "LabelFrame",
        "Radiobutton",
        "Checkbutton",
        "Treeview",
        "Progressbar",
        "Separator",
    ):
        setattr(ttk_module, widget_name, _StubTTKWidget)

    tk_module.messagebox = messagebox_module
    tk_module.ttk = ttk_module
    tk_module.simpledialog = simpledialog_module

    sys.modules["tkinter"] = tk_module
    sys.modules["tkinter.messagebox"] = messagebox_module
    sys.modules["tkinter.ttk"] = ttk_module
    sys.modules["tkinter.simpledialog"] = simpledialog_module


_install_tkinter_stub()
