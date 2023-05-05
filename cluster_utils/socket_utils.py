#!/usr/bin/env python
# -*- coding: utf-8 -*-

# @Time     : 2018.12
# @Software : Z3 Computing Cluster
# @Author   : Shichao Liao
# @Email    : liaosc@liaoshichao.com
# @Github   : https://github.com/liaoscdy

import socket
import datetime

from logger.cluster_logger import cluster_logger

MSG_END_TAG = '@@END@@'.encode('utf-8')
TCP_BUFFER_SIZE = 4096

def buffer_send(socket_fd, buffer):
    """
    raise exception
    :type socket_fd socket.socket
    :type buffer str
    :param socket_fd:
    :param buffer:
    :return:
    """
    socket_fd.send(buffer.encode('utf-8') + MSG_END_TAG)


def buffer_recv(socket_fd, timeout=5, blocked=False):
    """
    :type socket_fd socket.socket
    :type timeout float
    :param socket_fd:
    :param timeout:
    :param blocked:
    :return: bytes, is_net_break
    """
    recv_complete_data = bytes()
    recv_start = datetime.datetime.now()
    socket_fd.setblocking(blocked)
    while True:
        recv_current = datetime.datetime.now()
        if timeout < int((recv_current - recv_start).seconds):
            break
        try:
            recv_data = socket_fd.recv(TCP_BUFFER_SIZE)
        except BlockingIOError:
            continue
        except Exception as e:
            cluster_logger.warning("Error in recv tcp data. error: %s" %str(e))
            return bytes(), True
        recv_complete_data += recv_data
        if MSG_END_TAG in recv_complete_data:
            recv_complete_data = recv_complete_data[:recv_complete_data.find(MSG_END_TAG)]
            return recv_complete_data, False
    return bytes(), False
