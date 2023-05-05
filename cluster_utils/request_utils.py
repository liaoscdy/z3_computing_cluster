#!/usr/bin/env python
# -*- coding: utf-8 -*-

# @Time     : 2018.12
# @Software : Z3 Computing Cluster
# @Author   : Shichao Liao
# @Email    : liaosc@liaoshichao.com
# @Github   : https://github.com/liaoscdy

import json
import socket

from cluster_utils import socket_utils

def request_solver(ip, port, sexpr):
    send_msg = {
        "action": "solver",
        "sexpr": sexpr
    }
    client_socket = socket.socket()
    try:
        client_socket.connect((ip, port))
        socket_utils.buffer_send(client_socket, json.dumps(send_msg))
    except Exception as e:
        print("Error in connect %s:%s, msg: %s" %(ip, port, str(e)))
        return False

    recv_complete_data, _ = socket_utils.buffer_recv(client_socket)
    if len(recv_complete_data) == 0:
        print("Empty recv data.")
        return False

    recv_data_string = recv_complete_data.decode('utf-8', 'ignore')
    try:
        recv_data_json = json.loads(recv_data_string)
        print(recv_data_json)
    except json.JSONDecodeError:
        print("Error format of recv data.")
        return False

    return recv_data_json.get("result", False)


if __name__ == '__main__':
    import z3
    solver = z3.SimpleSolver()
    a = z3.BitVec("a", 256)
    solver.append(a > 10)
    solver.append(a < 20)

    print(request_solver("127.0.0.1", 8888, solver.sexpr()))
