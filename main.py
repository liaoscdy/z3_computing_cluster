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
from cluster_node.cluster_node import ClusterNode

import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Z3 Computing cluster. Project: https://github.com/liaoscdy/z3_computing_cluster')
    parser.add_argument("-n", "--node", help="[-t NODENAME], server or client.")
    parser.add_argument("-cpu", "--cpu", help="[-options num], If you choose client. "
                                              "How many cpu cores are provided for calculation? default=2")
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
        parser.print_help()
        print("Did not choose anything. The program exited.")

