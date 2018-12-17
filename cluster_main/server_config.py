#!/usr/bin/env python
# -*- coding: utf-8 -*-

# @Time     : 2018.12
# @Software : Z3 Computing Cluster
# @Author   : Shichao Liao
# @Email    : liaosc@liaoshichao.com
# @Github   : https://github.com/liaoscdy

# IP address of tcp listener
TcpHostIp = "127.0.0.1"
# Port of tcp listener
TcpHostPort = 8888
# Tcp queue length
TcpListening = 10

# Queue length waiting to be solved
SolverPending = 1000
# The frequency of checking queue timeout data
SolverCheckTime = 2
# Time to solve the expression
SolverTime = 100

ThreadWakeInterval = 0.2
