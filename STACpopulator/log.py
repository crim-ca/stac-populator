import argparse
import datetime as dt
import json
import logging.config

LOG_RECORD_BUILTIN_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


def setup_logging(ns: argparse.Namespace) -> None:
    """Set up the logger for the app."""
    config = _logconfig()
    if ns.log_file is not None:
        config["handlers"]["file"]["filename"] = ns.log_file
        config["handlers"]["file"]["level"] = ns.log_level_file
        config["loggers"]["root"]["handlers"].append("file")
    else:
        config["handlers"].pop("file")
    config["handlers"]["stderr"]["level"] = ns.log_level_stderr
    logging.config.dictConfig(config)


class JSONLogFormatter(logging.Formatter):
    """
    Log formatter for JSON logs.

    See: https://github.com/mCodingLLC/VideosSampleCode/tree/master/videos/135_modern_logging
    """

    def __init__(
        self,
        *,
        fmt_keys: dict[str, str] | None = None,
    ) -> None:
        super().__init__()
        self.fmt_keys = fmt_keys if fmt_keys is not None else {}

    def format(self, record: logging.LogRecord) -> str:
        """Return a formatted log entry."""
        message = self._prepare_log_dict(record)
        return json.dumps(message, default=str)

    def _prepare_log_dict(self, record: logging.LogRecord) -> dict:
        always_fields = {
            "message": record.getMessage(),
            "timestamp": dt.datetime.fromtimestamp(record.created, tz=dt.timezone.utc).isoformat(),
        }
        if record.exc_info is not None:
            always_fields["exc_info"] = self.formatException(record.exc_info)

        if record.stack_info is not None:
            always_fields["stack_info"] = self.formatStack(record.stack_info)

        message = {
            key: msg_val if (msg_val := always_fields.pop(val, None)) is not None else getattr(record, val)
            for key, val in self.fmt_keys.items()
        }
        message.update(always_fields)

        for key, val in record.__dict__.items():
            if key not in LOG_RECORD_BUILTIN_ATTRS:
                message[key] = val

        return message


def _logconfig() -> dict:
    """
    Generate a log configuration dictionary.

    This is not a global constant in case logging is dynamically updated
    after this module is loaded.
    Currently, this is only done in tests.
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "()": "colorlog.ColoredFormatter",
                "format": "  %(log_color)s%(levelname)s:%(reset)s %(blue)s[%(name)-30s]%(reset)s %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            },
            "json": {
                "()": f"{JSONLogFormatter.__module__}.{JSONLogFormatter.__name__}",
                "fmt_keys": {
                    "level": "levelname",
                    "message": "message",
                    "timestamp": "timestamp",
                    "logger": "name",
                    "module": "module",
                    "function": "funcName",
                    "line": "lineno",
                    "thread_name": "threadName",
                },
            },
        },
        "handlers": {
            "stderr": {
                "class": "logging.StreamHandler",
                "formatter": "simple",
                "stream": "ext://sys.stderr",
            },
            "file": {
                "class": "logging.FileHandler",
                "formatter": "json",
                "filename": "__",
            },
        },
        "loggers": {"root": {"level": "DEBUG", "handlers": ["stderr"]}},
    }


def add_logging_options(parser: argparse.ArgumentParser) -> None:
    """Add arguments to a parser to configure logging options."""
    parser.add_argument(
        "-l",
        "--log-level-stderr",
        choices=logging.getLevelNamesMapping(),
        default=logging.INFO,
        help="Level for logs written to stderr",
    )
    parser.add_argument(
        "-f",
        "--log-file",
        help=(
            "File to write log output to as well as stderr. "
            "File logs will be written in JSONL format. "
            "By default logs will be written to stderr only."
        ),
    )
    parser.add_argument(
        "-L",
        "--log-level-file",
        choices=logging.getLevelNamesMapping(),
        default=logging.INFO,
        help="Level for logs written to a file",
    )
