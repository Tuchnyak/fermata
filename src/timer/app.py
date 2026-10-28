import ttkbootstrap as ttk
from timer.ui.main_window import MainWindow


def main():
    root = ttk.Window(themename="darkly")
    MainWindow(root)
    root.mainloop()
