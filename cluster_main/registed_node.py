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
import select

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
        self.node_socket_fd.setblocking(0)
        self.node_net_connection = True
        self.cpu_core = cpu_core

    def run(self):
        registed = len(self.cluster_server.node_resource) < server_config.SolverNodeMax
        registed_msg = {
            "action":"registe",
            "registed":registed
        }
        try:
            socket_utils.buffer_send(self.node_socket_fd, json.dumps(registed_msg))
            cluster_logger.debug("Send registed receipt.")
        except Exception as e:
            registed = False
            cluster_logger.warning("Can't send registed msg to node. error: %s" %str(e))

        if not registed:
            self.cluster_server.node_resource_release(hash(self.node_socket_addr))
            return

        try:
            epoll = select.epoll()
            epoll.register(self.node_socket_fd.fileno(), select.EPOLLIN)
        except Exception as e:
            cluster_logger.warning("Epoll node_socket failed. error: %s" % str(e))
            self.cluster_server.node_resource_release(hash(self.node_socket_addr))
            return

        solver_pending = {}
        while True:
            if not self.cluster_server.is_server_running \
                or not self.node_net_connection:
                break

            solver_queue_item = None
            if len(solver_pending) < self.cpu_core:
                solver_queue_item = self.cluster_server.solver_queue_pop()

            epoll_events = epoll.poll(1)
            for fileno, event in epoll_events:
                if event & select.EPOLLIN:
                    recv_complete_data, _ = socket_utils.buffer_recv(self.node_socket_fd, timeout=0.5)
                    if len(recv_complete_data) == 0:
                        continue
                    try:
                        recv_data_string = recv_complete_data.decode('utf-8', 'ignore')

                        cluster_logger.debug("Get solver data: %s" % recv_data_string)

                        recv_data_json = json.loads(recv_data_string)
                        recv_action = recv_data_json.get("action", None)
                        if recv_action != "solver":
                            continue
                        solver_id = recv_data_json.get("solver_id", None)
                        solver_result = recv_data_json.get("result", None)
                        if solver_id is None or solver_result is None:
                            continue
                        if type(solver_result) is not bool:
                            solver_result = False

                        solver_item = solver_pending.get(solver_id, None)
                        if solver_item is not None:
                            solver_pending.pop(solver_id)
                            self.cluster_server.send_result(solver_item.socket_fd, solver_result)
                            solver_item.socket_fd.close()
                    except Exception as result_exception:
                        cluster_logger.warning("Error in recv/send node's result. msg: %s" % str(result_exception))
                if event & select.EPOLLHUP:
                    self.node_net_connection = False
                    print("closed!!!!!!!!!!!!!!!!!!")
                    cluster_logger.warning("ClusterNode Connect breaked.")
                    break
            # clean timeout requests
            self.clean_timeout(solver_pending)
            if solver_queue_item is not None:
                print("Get solver item: ", solver_queue_item.solver_id)
                solver_msg = {
                    "action":"solver",
                    "solver_id":solver_queue_item.solver_id,
                    "sexpr":solver_queue_item.z3_sexpr
                }
                try:
                    socket_utils.buffer_send(self.node_socket_fd, json.dumps(solver_msg))
                    solver_pending[solver_queue_item.solver_id] = solver_queue_item
                    print("send solver_item to node.")
                except Exception as send_exception:
                    cluster_logger.warning("Can't send solver request to node. msg: %s" %str(send_exception))
                    if not self.cluster_server.solver_queue_push(solver_queue_item):
                        solver_pending[solver_queue_item.solver_id] = solver_queue_item

        self.release_pending(solver_pending)
        try:
            shutdown_msg = {
                "action":"control",
                "cmd":"shutdown"
            }
            socket_utils.buffer_send(self.node_socket_fd, json.dumps(shutdown_msg))
            self.node_socket_fd.shutdown(socket.SHUT_RDWR)
            self.node_socket_fd.close()
        except Exception as e:
            cluster_logger.info("Shutdonw socket: %s, Ignore error: %s" %(self.node_socket_addr, str(e)))
        self.cluster_server.node_resource_release(hash(self.node_socket_addr))

    def clean_timeout(self, solver_pending):
        """
        :type solver_pending dict
        :param solver_pending: 
        :return: 
        """
        keys = solver_pending.keys()
        remove_keys = []
        for solver_id in keys:
            solver_item = solver_pending[solver_id]
            current_time = datetime.datetime.now()
            used_time = int((current_time - solver_item.pending_time).seconds)
            if used_time > server_config.SolverTime:
                cluster_logger.info("Deleted timeout solver requests.")
                remove_keys.append(solver_id)
                self.cluster_server.send_result(solver_item.socket_fd, False)

        for remove_key in remove_keys:
            solver_pending.pop(remove_key)

    def release_pending(self, solver_pending):
        for solver_item in solver_pending:
            if not self.cluster_server.solver_queue_push(solver_item):
                self.cluster_server.send_result(solver_item.socket_fd, False)
