import logging
import os.path

import coloredlogs
import sys
from typing import Dict
from enum import Enum


class LogLevels(Enum):
    debug = 'DEBUG'
    info = 'INFO'
    warning = 'WARNING'
    error = 'ERROR'
    critical = 'CRITICAL'


class Log:

    def __init__(self):
        self.filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../..', 'logs.log')
        self.console_output_handler = logging.StreamHandler(stream=sys.stdout)
        self.file_output_handler = logging.FileHandler(filename=self.filename)
        self.set_console_format()
        self.set_logfile_format()

    def set_console_format(self):
        colored_formatter = coloredlogs.ColoredFormatter(
            fmt='[ %(asctime)s ] |%(levelname)-7s| %(filename)-18s line: %(lineno)-3d %(message)s',
            level_styles=dict(
                debug=dict(color='white'),
                info=dict(color='blue'),
                warning=dict(color='yellow', bright=True),
                error=dict(color='red', bold=True, bright=True),
                critical=dict(color='black', bold=True, background='red'),
            ),
            field_styles=dict(
                name=dict(color='white'),
                asctime=dict(color='white'),
                funcName=dict(color='white'),
                lineno=dict(color='white'),
            )
        )
        self.console_output_handler.setFormatter(fmt=colored_formatter)

    def set_logfile_format(self):
        file_formatter = logging.Formatter(fmt='[ %(asctime)s ] |%(levelname)-5s| %(filename)-18s line: %(lineno)-3d %(message)s')
        self.file_output_handler.setFormatter(file_formatter)

    def logger(self, name) -> logging.Logger:
        logging.basicConfig()
        logger = logging.getLogger(name)
        coloredlogs.install(logger=logger)
        logger.propagate = False
        logger.addHandler(hdlr=self.console_output_handler)
        logger.addHandler(hdlr=self.file_output_handler)
        return logger

    def change_logger(self, name: str, level: LogLevels):
        if name in logging.root.manager.loggerDict.keys():
            logging.root.manager.loggerDict[name] = self.logger(name)
            self.set_log_levels_for_modules({name: level})

    @staticmethod
    def list_loggers() -> Dict[str, logging.Logger]:
        return {name: logging.getLogger(name) for name in logging.root.manager.loggerDict}

    def set_log_level(self, level: LogLevels = LogLevels.debug):
        for logger_ in self.list_loggers().values():
            logger_.setLevel(level.value)

    def set_log_levels_for_modules(self, modules_by_name: Dict[str, LogLevels]):
        for module_name, module in self.list_loggers().items():
            if modules_by_name.get(module_name):
                self.list_loggers()[module_name].setLevel(modules_by_name[module_name].value)

    def clear_log_file(self):
        self.file_output_handler.stream.truncate(0)


service = Log()
