import functools
from tkinter import messagebox
import os
import shutil


def gui_error_handler(func):
    """
    A decorator to handle database-related errors in Tkinter GUI functions.

    This decorator catches database-related exceptions and displays an appropriate
    message box for the user, allowing them to retry or cancel the operation.

    Does not log any errors, only catches errors by the pyodbc wrapper defined in mie_trak_funcs.py.

    :type logger: logging.Logger or None
    :return: A wrapped function with error handling.
    :rtype: Callable
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        while True:
            try:
                return func(*args, **kwargs)
            except RuntimeError as e:  # Catching RuntimeError from `with_db_conn`
                if hasattr(self, "loading_screen") and self.loading_screen:
                    self.loading_screen.after(0, self.loading_screen.destroy)

                retry = messagebox.askretrycancel(
                    title="Database Error",
                    message=f"{e}\n\nWould you like to retry?",
                )
                if not retry:
                    return None  # Exit function on cancel
            except Exception as e:
                if hasattr(self, "loading_screen") and self.loading_screen:
                    self.loading_screen.after(0, self.loading_screen.destroy)

                messagebox.showerror(
                    title="Unexpected Error",
                    message=f"An unexpected error occurred:\n\n{e}",
                )
                return None  # Exit function

    return wrapper


def center_window(window, width=1000, height=700):
    """
    Centers a Tkinter window on the screen with the specified dimensions.

    Parameters:
        window (Tk or Toplevel): The Tkinter window instance to be centered.
        width (int): The desired width of the window in pixels (default is 1000).
        height (int): The desired height of the window in pixels (default is 700).

    The function calculates the center position based on the screen's dimensions and sets
    the window geometry accordingly.
    """

    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)

    window.geometry(f"{width}x{height}+{x}+{y}")


def transfer_file_to_folder(folder_path: str, file_path: str) -> str:
    """
    Copies a file to the specified folder and returns the new file path.

    This function ensures that the destination folder exists, then copies the file
    from the given source path to that folder, preserving the original filename.

    Parameters:
        folder_path (str): The path to the destination folder where the file should be copied.
        file_path (str): The full path to the source file that will be copied.

    Returns:
        str: The full path to the copied file in the destination folder.
    """

    os.makedirs(folder_path, exist_ok=True)

    filename = os.path.basename(file_path)  # source file path
    destination_path = os.path.join(folder_path, filename)
    shutil.copyfile(file_path, destination_path)

    return destination_path
