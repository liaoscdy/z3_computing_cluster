#!/usr/bin/env python
# -*- coding: utf-8 -*-

# @Time     : 2018.12
# @Software : Z3 Computing Cluster
# @Author   : Shichao Liao
# @Email    : liaosc@liaoshichao.com
# @Github   : https://github.com/liaoscdy

import socket
import threading
import json
import time
import datetime

from logger.cluster_logger import cluster_logger
from cluster_main import server_config
from cluster_main.registed_node import RegistedNode
from cluster_utils import socket_utils

class SolverQueueItem:
    """
    has solver socket_fd, and z3_sexpr
    push into solver_queue
    """

    def __init__(self, socket_fd, z3_sexpr):
        """
        :param socket_fd: object of socket.socket
        :param z3_sexpr: string of z3 expression
        """
        self.socket_fd = socket_fd
        self.z3_sexpr = z3_sexpr
        self.pending_time = datetime.datetime.now()

class ClusterServer:

    def __init__(self):
        self.is_server_running = False
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # key:id, value:result
        self.solver_completed = {}
        self.solver_thread = {}
        self.solver_queue = []
        self.solver_queue_mutex = threading.Lock()
        # key:hash(address), value:registed_node
        self.node_resource = {}
        self.node_resource_mutex = threading.Lock()

    def server_start(self):
        try:
            self.server_socket.bind((server_config.TcpHostIp, server_config.TcpHostPort))
            self.server_socket.listen(server_config.TcpListening)
            self.is_server_running = True
        except Exception as server_exception:
            cluster_logger.error("Server can't start, error: ", server_exception)

        cluster_logger.info("ClusterServer Start!")
        # Thread for clean timeout pending solver
        timeout_check = threading.Thread(target=ClusterServer.handle_timeout, args=(self,))
        self.node_resource_append("handle_timeout", timeout_check)
        timeout_check.start()
        while True:
            if not self.is_server_running:
                break

            try:
                client_socket, client_addr = self.server_socket.accept()
            except Exception as accept_exception:
                cluster_logger.error("Error in server accept, msg: ", accept_exception)
                break

            recv_complete_data = socket_utils.buffer_recv(client_socket)
            if len(recv_complete_data) == 0:
                cluster_logger.warning("Recv data is None.")
                continue

            recv_data_string = recv_complete_data.decode('utf-8', 'ignore')
            try:
                recv_data_json = json.loads(recv_data_string)
            except json.JSONDecodeError:
                cluster_logger.warning("Error format of recv data.")
                continue

            action = recv_data_json.get("action", None)
            if action == "registe_node":
                cpu_core = recv_data_json.get("cpu_core", None)
                if cpu_core is not None and cpu_core.isdigit():
                    registed_node = RegistedNode(self, client_socket, client_addr, int(cpu_core))
                    self.node_resource_append(hash(client_addr), registed_node)
                    registed_node.start()

            if action == "solver":
                solver_sexpr = recv_data_json.get("sexpr", None)
                if solver_sexpr is not None:
                    self.solver_queue_lock()
                    if len(self.solver_queue) < server_config.SolverPending:
                        solver_queue_item = SolverQueueItem(client_socket, solver_sexpr)
                        self.solver_queue.append(solver_queue_item)
                    self.solver_queue_unlock()
                else:
                    ClusterServer.send_result(client_socket, False)

            if action == "shutdown":
                self.server_stop()
                break

        self.server_wait_release()
        cluster_logger.info("ClusterServer is Stoped.")

    def server_stop(self):
        self.is_server_running = False

    def server_wait_release(self):
        while True:
            time.sleep(server_config.ThreadWakeInterval)
            if len(self.node_resource) == 0:
                break

    def solver_queue_lock(self):
        self.solver_queue_mutex.acquire()

    def solver_queue_unlock(self):
        self.solver_queue_mutex.release()

    def solver_queue_pop(self):
        queue_item = None
        with self.solver_queue_mutex:
            if len(self.solver_queue) > 0:
                queue_item = self.solver_queue.pop()
        return queue_item

    def node_resource_release(self, key):
        """
        release Thread resource
        :param key:
        :return:
        """
        with self.node_resource_mutex:
            if self.node_resource.get(key, None) is not None:
                self.node_resource.pop(key)

    def node_resource_append(self, key, value):
        """
        append node resource
        :param key:
        :param value:
        :return:
        """
        with self.node_resource_mutex:
            self.node_resource[key] = value


    @staticmethod
    def send_result(socket_fd, result=False):
        """
        :type socket_fd socket.socket
        :param socket_fd:
        :param result:
        :return:
        """
        try:
            socket_utils.buffer_send(socket_fd, json.dumps({"result":result}))
            socket_fd.close()
        except Exception as send_exception:
            cluster_logger.warning("Can't send to client. msg: %s" %str(send_exception))


    @staticmethod
    def handle_timeout(cluster_server):
        """
        :type cluster_server ClusterServer
        :param cluster_server:
        :return:
        """
        while True:
            if not cluster_server.is_server_running:
                break

            time.sleep(server_config.SolverCheckTime)
            cluster_server.solver_queue_lock()
            valid_solver_queue = []
            for solver_item in cluster_server.solver_queue:
                current_time = datetime.datetime.now()
                used_time = int((current_time - solver_item.pending_time).seconds)
                if used_time < server_config.SolverTime:
                    valid_solver_queue.append(solver_item)
                else:
                    ClusterServer.send_result(solver_item.socket_fd, False)
            cluster_server.solver_queue = valid_solver_queue
            cluster_server.solver_queue_unlock()
