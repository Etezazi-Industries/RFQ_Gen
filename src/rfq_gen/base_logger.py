import sys
import loguru


def getlogger(name: str = "DefaultName", level="DEBUG") -> loguru.logger:  # type: ignore
    """
    Initialize and return a logger instance with the specified name and level.
    """
    logobj = loguru.logger.bind(name=name)

    logobj.remove()

    logger_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "{extra[name]} | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    if sys.stderr:
        logobj.add(
            sys.stderr,
            level=level,
            format=logger_format,
            colorize=True,
            serialize=False,
        )

    # NOTE: to get logs into a file for prod.
    logobj.add(
        r"Z:\dist\logs\RFQ_GEN.log",  # Specify your desired log file path
        level=level,
        format=logger_format,
        colorize=False,  # No color in file logs
        serialize=False,
        rotation="10 MB",  # Automatically rotate after 10 MB
        retention="7 days",  # Keep logs for 7 days
        compression="zip",  # Compress rotated logs
    )

    return logobj
