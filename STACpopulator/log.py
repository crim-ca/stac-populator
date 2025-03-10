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


def setup_logging(logfname: str, log_level: int) -> None:
    """Setup the logger for the app.

    :param logfname: name of the file to which to write log outputs
    :type logfname: str
    :param log_level: base logging level (e.g. "INFO")
    :type log_level: str
    """
    config = logconfig
    config["handlers"]["file"]["filename"] = logfname
    for handler in config["handlers"]:
        config["handlers"][handler]["level"] = logging.getLevelName(log_level)
    logging.config.dictConfig(config)


class JSONLogFormatter(logging.Formatter):
    # From: https://github.com/mCodingLLC/VideosSampleCode/tree/master/videos/135_modern_logging
    def __init__(
        self,
        *,
        fmt_keys: dict[str, str] | None = None,
    ):
        super().__init__()
        self.fmt_keys = fmt_keys if fmt_keys is not None else {}

    def format(self, record: logging.LogRecord) -> str:
        message = self._prepare_log_dict(record)
        return json.dumps(message, default=str)

    def _prepare_log_dict(self, record: logging.LogRecord):
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


class NonErrorFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool | logging.LogRecord:
        return record.levelno <= logging.INFO


logconfig = {
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
            "level": "INFO",
            "formatter": "simple",
            "stream": "ext://sys.stderr",
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": "__added_dynamically__",
        },
    },
    "loggers": {"root": {"level": "DEBUG", "handlers": ["stderr", "file"]}},
}


def add_logging_options(parser: argparse.ArgumentParser) -> None:
    """
    Adds arguments to a parser to configure logging options.
    """
    parser.add_argument("--debug", action="store_const", const=logging.DEBUG, help="set logger level to debug")
    parser.add_argument(
        "--log-file",
        default=f"stac_populator_log_{dt.datetime.now(dt.timezone.utc).isoformat() + 'Z'}.jsonl",
        help="file to write log output to. By default logs will be written to the current directory.",
    )
