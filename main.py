#!/usr/bin/env python
# -*- coding: utf-8 -*-

# @Time     : 2018.12
# @Software : Z3 Computing Cluster
# @Author   : Shichao Liao
# @Email    : liaosc@liaoshichao.com
# @Github   : https://github.com/liaoscdy

import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from cluster_main.cluster_server import ClusterServer
from cluster_main import server_config
from cluster_node.cluster_node import ClusterNode
from cluster_node import node_config
from cluster_utils import socket_utils

import argparse
import socket
import json

def close_cluster_server():
    send_msg = {
        "action": "control",
        "cmd": "shutdown"
    }
    control_socket = socket.socket()
    try:
        control_socket.connect((server_config.TcpHostIp, server_config.TcpHostPort))
        socket_utils.buffer_send(control_socket, json.dumps(send_msg))
        control_socket.close()
        print("Shutdown Server Success.")
    except Exception as e:
        print("Can't shutdown server. error: %s" %str(e))

def close_cluster_node():
    socket_client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        socket_client.connect(node_config.ControlSocket)
        socket_client.send('shutdown'.encode('utf-8'))
        socket_client.close()
        print("Shutdown Node Success.")
    except Exception as e:
        print("Can't shutdown ClientNode. error: %s" %str(e))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Z3 Computing cluster. Project: https://github.com/liaoscdy/z3_computing_cluster')
    parser.add_argument("-n", "--node", help="[-t server/client], server or client.")
    parser.add_argument("-cpu", "--cpu", help="[-options num], If you choose client. "
                                              "How many cpu cores are provided for calculation? default=2")
    parser.add_argument("-e", "--exit", help="[-e server/client], Close the server or client.")
    args = parser.parse_args()

    cpu_core = 2
    if args.cpu is not None and args.cpu.isdigit():
        provide_cpu = int(args.cpu)
        cpu_core = provide_cpu if provide_cpu > 0 else cpu_core

    tool = args.node
    if tool == 'server':
        cluster_server = ClusterServer()
        cluster_server.server_start()
    elif tool == 'client':
        cluster_node = ClusterNode(cpu_core)
        cluster_node.node_start()
    else:
        exit_tool = args.exit
        exit_funcs = {
            'server':close_cluster_server,
            'client':close_cluster_node
        }
        func = exit_funcs.get(exit_tool, None)
        if func is None:
            parser.print_help()
        else:
            func()
