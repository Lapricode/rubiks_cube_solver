#!/usr/bin/python3
import tkinter as tk

from rubik.ui.app import RubiksCubeApp


def main() -> None:
    root = tk.Tk()
    RubiksCubeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
