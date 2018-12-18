#!/usr/bin/env python
# -*- coding: utf-8 -*-

# @Time     : 2018.12
# @Software : Z3 Computing Cluster
# @Author   : Shichao Liao
# @Email    : liaosc@liaoshichao.com
# @Github   : https://github.com/liaoscdy

import sys
import os

ServerIP = ""

ServerPort = 8888
ServerConnectRetry = 20

SolverTime = 50000

ThreadWakeInterval = 0.2

ControlSocket = sys.path.append(os.path.abspath(os.path.dirname(__file__)) + "/../runtime/node_client_socket")
