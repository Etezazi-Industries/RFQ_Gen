import os
import sys
import pyodbc
import functools
from contextlib import closing
from base_logger import getlogger
from typing import Optional, Annotated, Dict, Any, Callable, List
from pydantic import BaseModel, Field, conint, constr, confloat
from dotenv import load_dotenv


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # type: ignore
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


env_path = resource_path(".env")
load_dotenv(env_path)

LOGGER = getlogger("MT Funcs")

conn_type = "LIVE"  # WARNING: Change this to live when compiling
LOGGER.info(f"Database conn: {conn_type}")
DSN = os.getenv(conn_type)


def with_db_conn(commit: bool = False):
    """
    A decorator to manage database connections using pyodbc.

    This decorator automatically handles connection management, commits transactions
    if specified, and properly closes the cursor and connection. If an error occurs,
    it logs the error and propagates the exception to be handled at a higher level.

    :param commit: If True, commits the transaction after function execution.
    :type commit: bool
    :return: A wrapped function with database connection handling.
    :rtype: Callable
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                with pyodbc.connect(DSN) as conn:
                    with closing(conn.cursor()) as cursor:
                        result = func(cursor, *args, **kwargs)

                        if commit:
                            conn.commit()

                        return result
            except pyodbc.OperationalError as vpn_err:
                error_msg = (
                    f"VPN not connected. Could not connect to the database.\n{vpn_err}"
                )
                LOGGER.error(error_msg)
                raise RuntimeError(error_msg)
            except pyodbc.Error as db_err:
                error_msg = f"Database Error in {func.__name__}: {db_err}"
                LOGGER.error(error_msg)
                raise RuntimeError(error_msg)
            except ValueError as val_err:
                LOGGER.error(val_err)
                raise ValueError(val_err)
            except Exception as e:
                error_msg = f"Unexpected Error in {func.__name__}: {e}"
                LOGGER.error(error_msg)
                raise RuntimeError(error_msg)

        return wrapper

    return decorator


@with_db_conn()
def get_table_schema(cursor, table_name: str) -> List[Dict[str, Any]]:
    """
    [TODO:description]

    :param table_name: [TODO:description]
    """
    query = f"""
    SELECT 
        COLUMN_NAME, 
        DATA_TYPE, 
        CHARACTER_MAXIMUM_LENGTH, 
        IS_NULLABLE 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = ?
    """
    cursor.execute(query, (table_name,))
    schema = []

    for row in cursor.fetchall():
        schema.append(
            {
                "column_name": row.COLUMN_NAME,
                "data_type": row.DATA_TYPE,
                "max_length": row.CHARACTER_MAXIMUM_LENGTH,
                "is_nullable": row.IS_NULLABLE == "YES",
            }
        )

    return schema


SQL_TO_PYDANTIC = {
    "int": conint(ge=0),
    "bigint": conint(),
    "smallint": conint(),
    "tinyint": conint(),
    "decimal": confloat(),
    "numeric": confloat(),
    "float": confloat(),
    "real": confloat(),
    "bit": bool,
    "varchar": str,
    "nvarchar": str,
    "char": str,
    "nchar": str,
    "text": str,
}


def create_pydantic_model(table_name: str):
    """
    [TODO:description]

    :param table_name: [TODO:description]
    :param schema: [TODO:description]
    """

    schema = get_table_schema(table_name)

    annotations = {}
    for column in schema:
        col_name = column["column_name"]
        sql_type = column["data_type"]
        max_length = column["max_length"]
        is_nullable = column["is_nullable"]

        if col_name.lower().endswith("pk"):
            is_nullable = True

        pydantic_type = SQL_TO_PYDANTIC.get(sql_type, str)

        if sql_type in ("varchar", "nvarchar", "char", "nchar", "text"):
            if max_length is not None and max_length > 0:
                pydantic_type = constr(max_length=max_length)

        if is_nullable:
            pydantic_type = Optional[pydantic_type]

        annotations[col_name] = Annotated[
            pydantic_type, Field(None if is_nullable else ..., title=col_name)
        ]

    namespace = {"__annotations__": annotations}
    return type(f"{table_name.capitalize()}Model", (BaseModel,), namespace)
