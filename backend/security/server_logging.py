from gunicorn.glogging import Logger
from .observability import OperationalFormatter


class PrivateGunicornLogger(Logger):
    def setup(self, cfg):
        super().setup(cfg)
        for logger in (self.error_log, self.access_log):
            for handler in logger.handlers:
                handler.setFormatter(OperationalFormatter())
