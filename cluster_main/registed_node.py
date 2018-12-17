#!/usr/bin/env python
# -*- coding: utf-8 -*-

# @Time     : 2018.12
# @Software : Z3 Computing Cluster
# @Author   : Shichao Liao
# @Email    : liaosc@liaoshichao.com
# @Github   : https://github.com/liaoscdy

import json
import time
import threading
import datetime
import socket

from cluster_main import server_config
from cluster_utils import socket_utils
from logger.cluster_logger import cluster_logger

class RegistedNode(threading.Thread):

    def __init__(self, cluster_server, socket_fd, socket_addr, cpu_core):
        """
        :type socket_fd socket.socket
        :param cluster_server:
        :param socket_fd:
        :param socket_addr:
        :param cpu_core:
        """
        threading.Thread.__init__(self)
        self.cluster_server = cluster_server
        self.node_socket_fd = socket_fd
        self.node_socket_addr = socket_addr
        self.node_net_connection = True
        self.cpu_core = cpu_core
        self.invoke_thread = {}

    def run(self):
        while True:
            time.sleep(server_config.ThreadWakeInterval)
            if not self.cluster_server.is_server_running \
                or not self.node_net_connection:
                break

            if len(self.invoke_thread) == self.cpu_core:
                continue

            solver_item = self.cluster_server.solver_queue_pop()
            if solver_item is None:
                continue

            invoke_id = hash(datetime.datetime.now())
            invoke_thread = threading.Thread(target=RegistedNode.invoke_node_compute,
                             args=(self, solver_item, invoke_id))
            self.invoke_thread[invoke_id] = invoke_thread
            invoke_thread.start()

        self.cluster_server.node_resource_release(hash(self.node_socket_addr))

    def invoke_thread_release(self, key, net_breaked=False):
        if self.invoke_thread.get(key, None) is not None:
            self.invoke_thread.pop(key)
        if net_breaked:
            self.node_net_connection = False

    @staticmethod
    def invoke_node_compute(registed_node, solver_item, invoke_id):
        """
        :type registed_node RegistedNode
        :param registed_node:
        :param solver_item:
        :param invoke_id:
        :return:
        """

        socket_fd = solver_item.socket_fd
        z3_sexpr = solver_item.z3_sexpr
        pending_time = solver_item.pending_time
        invoke_begin = datetime.datetime.now()
        timeout = server_config.SolverTime - (int((invoke_begin - pending_time).seconds))
        if timeout <= 0:
            registed_node.cluster_server.send_result(socket_fd, False)
            registed_node.invoke_thread_release(invoke_id)
            return

        try:
            socket_utils.buffer_send(registed_node.node_socket_fd, json.dumps({"sexpr":z3_sexpr}))
        except Exception as invoke_send_exception:
            cluster_logger.warning("Can't send z3_sexpr to node. msg: %s" %str(invoke_send_exception))
            registed_node.cluster_server.send_result(socket_fd, False)
            registed_node.invoke_thread_release(invoke_id, net_breaked=True)
            return

        recv_complete_data = socket_utils.buffer_recv(registed_node.node_socket_fd, timeout)
        if len(recv_complete_data) == 0:
            registed_node.cluster_server.send_result(socket_fd, False)
            registed_node.invoke_thread_release(invoke_id)
            return

        try:
            recv_data_string = recv_complete_data.decode('utf-8', 'ignore')
            recv_data_json = json.loads(recv_data_string)
            solver_result = recv_data_json.get("result", False)
            if type(solver_result) is not bool:
                solver_result = False

            registed_node.cluster_server.send_result(socket_fd, solver_result)
        except Exception as result_exception:
            cluster_logger.warning("Error in recv node's result. msg: %s" %str(result_exception))
        registed_node.invoke_thread_release(invoke_id)
