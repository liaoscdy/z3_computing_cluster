#!/usr/bin/env python
# -*- coding: utf-8 -*-

# @Time     : 2018.12
# @Software : Z3 Computing Cluster
# @Author   : Shichao Liao
# @Email    : liaosc@liaoshichao.com
# @Github   : https://github.com/liaoscdy

from cloghandler import ConcurrentRotatingFileHandler
from logger import logger_config

import logging
import threading


class ClusterLogger:
    """
    use ConcurrentRotatingFileHandler for multiprocess
    """

    _is_created = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(ClusterLogger, "_instance"):
            with ClusterLogger._instance_lock:
                if not hasattr(ClusterLogger, "_instance"):
                    ClusterLogger._instance = object.__new__(cls)
        return ClusterLogger._instance

    def __init__(self):
        if ClusterLogger._is_created is None:
            self._cluster_logger = logging.getLogger(logger_config.LoggerName)
            self._cluster_logger.setLevel(logger_config.LoggerLevel)

            formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
            rotate_handler = ConcurrentRotatingFileHandler(logger_config.LogFile, "a",
                                                           logger_config.LoggerFileSize, encoding="utf-8")
            rotate_handler.setFormatter(formatter)
            self._cluster_logger.addHandler(rotate_handler)

    def debug(self, msg):
        self._cluster_logger.debug(str(msg))

    def info(self, msg):
        self._cluster_logger.info(str(msg))

    def warning(self, msg):
        self._cluster_logger.warning(str(msg))

    def error(self, msg):
        self._cluster_logger.error(str(msg))

cluster_logger = ClusterLogger()