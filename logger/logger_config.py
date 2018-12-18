#!/usr/bin/env python
# -*- coding: utf-8 -*-

# @Time     : 2018.12
# @Software : Z3 Computing Cluster
# @Author   : Shichao Liao
# @Email    : liaosc@liaoshichao.com
# @Github   : https://github.com/liaoscdy

import os

# 日志文件名称
LoggerName = "cluster_logger"
# 日志文件路径
LogFile = os.path.abspath(os.path.dirname(__file__) + os.path.sep + "../runtime/cluster.log")
# 日志等级
LoggerLevel = "DEBUG"
# 单个日志文件大小
LoggerFileSize = 1024 * 1024 * 100

