#!/usr/bin/env python
# -*- coding: utf-8 -*-

# @Time     : 2018.12
# @Software : Z3 Computing Cluster
# @Author   : Shichao Liao
# @Email    : liaosc@liaoshichao.com
# @Github   : https://github.com/liaoscdy

import z3
import socket
import json
import queue
import threading
import time
import os
import multiprocessing

from cluster_node import node_config
from cluster_utils import socket_utils
from logger.cluster_logger import cluster_logger

class ClusterNode:

    def __init__(self, cpu_core):
        self.cpu_core = cpu_core
        self.node_socket = None
        self.node_running = False

        self.compute_pool = None
        self.compute_result_queue = queue.Queue()
        self.result_deal_thread = None
        self.control_thread = None

    def node_start(self):
        if not self.node_connect():
            cluster_logger.error("Can't connect to server. shutdown")
            return

        self.compute_pool = multiprocessing.Pool(processes=self.cpu_core)
        self.control_thread = threading.Thread(target=ClusterNode.node_control_thread, args=(self,))
        self.control_thread.start()
        self.result_deal_thread = threading.Thread(target=ClusterNode.solver_result_queue, args=(self,))
        self.result_deal_thread.start()
        while True:
            if not self.node_running:
                break

            recv_complete_data, net_breaked = socket_utils.buffer_recv(self.node_socket)
            if net_breaked:
                if not self.node_connect():
                    self.node_running = False
                    cluster_logger.error("Can't connect to server. shutdown")
                    break
                continue

            if len(recv_complete_data) == 0:
                continue

            recv_data_string = recv_complete_data.decode('utf-8', 'ignore')
            try:
                recv_data_json = json.loads(recv_data_string)
            except json.JSONDecodeError:
                cluster_logger.debug("Json decodeError. recv_data: %s" %recv_data_string)
                continue

            action = recv_data_json.get("action", None)
            if action == "control":
                if recv_data_json.get("cmd", None) == "shutdown":
                    self.node_running = False
                    break

            if action == "solver":
                solver_id = recv_data_json.get("solver_id", None)
                sexpr = recv_data_json.get("sexpr", None)
                if sexpr is None or solver_id is None:
                    continue
                solver_thread = threading.Thread(target=ClusterNode.solver_thread, args=(self, sexpr, solver_id))
                solver_thread.start()

        try:
            self.node_socket.shutdown(socket.SHUT_RDWR)
            self.node_socket.close()
        except Exception as e:
            cluster_logger.warning("Can't shutdonw socket, Ignore. error: %s" %str(e))
        self.result_deal_thread.join()
        self.compute_pool.close()
        self.compute_pool.join()

    def node_registed(self):
        """
        connect and registed
        :return:
        """
        registe_node = {
            "action": "registe",
            "cpu_core": self.cpu_core
        }
        try:
            self.node_socket.connect((node_config.ServerIP, node_config.ServerPort))
            socket_utils.buffer_send(self.node_socket, json.dumps(registe_node))
            registe_recv, _ = socket_utils.buffer_recv(self.node_socket)
            if len(registe_recv) > 0:
                recv_data_string = registe_recv.decode('utf-8', 'ignore')
                recv_data_json = json.loads(recv_data_string)
                if recv_data_json['action'] == 'registe':
                    if recv_data_json['registed'] is True:
                        return True
        except Exception as e:
            cluster_logger.error("Registed Error, connect %s, msg: %s" % (node_config.ServerIP, str(e)))
        return False

    def node_connect(self):
        """
        connect to the ClusterServer
        :return:
        """
        self.node_socket = socket.socket()
        connect_retry = 0
        connect_success = False
        while connect_retry < node_config.ServerConnectRetry:
            if self.node_registed():
                connect_success = True
                break
            connect_retry += 1
            time.sleep(node_config.ThreadWakeInterval * connect_retry)
        return connect_success


    @staticmethod
    def solver_result_queue(cluster_node):
        """
        :type cluster_node ClusterNode
        :param cluster_node:
        :return:
        """
        while True:
            time.sleep(node_config.ThreadWakeInterval)
            if not cluster_node.node_running:
                break

            try:
                queue_item = cluster_node.compute_result_queue.get(timeout=node_config.ThreadWakeInterval)
            except queue.Empty:
                continue

            solver_id = queue_item.keys()[0]
            solver_result = queue_item[solver_id]
            solver_msg = {
                "action":"solver",
                "solver_id":solver_id,
                "result":solver_result
            }
            try:
                socket_utils.buffer_send(cluster_node.node_socket, json.dumps(solver_msg))
            except Exception as e:
                cluster_logger.error("Can't send result to server. msg: %s" %str(e))
                continue

    @staticmethod
    def solver_thread(cluster_node, sexpr, solver_id):
        """
        :type cluster_node ClusterNode
        :type sexpr str
        :param cluster_node:
        :param sexpr:
        :param solver_id:
        :return:
        """
        solver_result = cluster_node.compute_pool.apply_async(ClusterNode.solver_sexpr, (sexpr,))
        cluster_node.compute_result_queue.put({solver_id:solver_result})

    @staticmethod
    def solver_sexpr(sexpr):
        solver = z3.SimpleSolver()
        solver.from_string(sexpr)
        solver.set("timeout", node_config.SolverTime)
        try:
            result = solver.check()
            if result == z3.sat:
                return True
            else:
                return False
        except Exception as e:
            cluster_logger.warning("Error in solver. msg: %s" %str(e))
            return False

    @staticmethod
    def node_control_thread(cluster_node):
        """
        :type cluster_node ClusterNode
        :param cluster_node:
        :return:
        """
        control_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            control_socket.bind(node_config.ControlSocket)
        except OSError:
            os.remove(node_config.ControlSocket)
            control_socket.bind(node_config.ControlSocket)
        control_socket.listen(1)
        while True:
            try:
                conn, addr = control_socket.accept()
                msg = conn.recv(4096)
                msg = msg.decode('utf-8')
                if msg == 'shutdown':
                    cluster_logger.info("Recv client shutdown cmd.")
                    break
            except Exception as e:
                cluster_logger.error("Error in ClusterNode control loop! Error: %s" % str(e))
                break

        cluster_node.node_running = False
