#!/usr/bin/env python
# -*- coding: utf-8 -*-

# @Time     : 2018.12
# @Software : Z3 Computing Cluster
# @Author   : Shichao Liao
# @Email    : liaosc@liaoshichao.com
# @Github   : https://github.com/liaoscdy

# IP address of tcp listener
TcpHostIp = "0.0.0.0"
# Port of tcp listener
TcpHostPort = 8888
# Tcp queue length
TcpListening = 10
# Tcp read timeout
TcpReadTimeout = 10

# The max number of registed solver node.
SolverNodeMax = 1000
# Queue length waiting to be solved
SolverPending = 1000
# The frequency of checking queue timeout data
SolverCheckTime = 2
# Time to solve the expression
SolverTime = 50

ThreadWakeInterval = 0.2
