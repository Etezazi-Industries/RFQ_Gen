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
        while True:
            try:
                return func(*args, **kwargs)
            except RuntimeError as e:  # Catching RuntimeError from `with_db_conn`
                retry = messagebox.askretrycancel(
                    title="Database Error",
                    message=f"{e}\n\nWould you like to retry?",
                )
                if not retry:
                    return None  # Exit function on cancel
            except Exception as e:
                messagebox.showerror(
                    title="Unexpected Error",
                    message=f"An unexpected error occurred:\n\n{e}",
                )
                return None  # Exit function

    return wrapper


def center_window(window, width=1000, height=700):
    """
    [TODO:description]

    :param window [TODO:type]: [TODO:description]
    :param width [TODO:type]: [TODO:description]
    :param height [TODO:type]: [TODO:description]
    """
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)

    window.geometry(f"{width}x{height}+{x}+{y}")


def transfer_file_to_folder(folder_path: str, file_path: str) -> str:
    """
    [TODO:description]

    :param folder_path: [TODO:description]
    :param file_path: [TODO:description]
    :return: [TODO:description]
    """

    os.makedirs(folder_path, exist_ok=True)

    filename = os.path.basename(file_path)  # source file path
    destination_path = os.path.join(folder_path, filename)
    shutil.copyfile(file_path, destination_path)

    return destination_path
