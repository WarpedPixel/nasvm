#!/usr/bin/env python3
import asyncio
import websockets
import json
import keyring
import getpass
import os
import argparse

def nas_socketname(server):
    return f"ws://{server}/websocket"

# creates an authenticated API session, returns the ID for further calls
async def nas_create_session(server, websocket):
    await websocket.send(json.dumps({
        "msg": "connect",
        "version": "1",
        "support": ["1"]
        }))
    greeting = await websocket.recv()
    if args.verbosity >= 3:
        print(f"< {greeting}")

    if not json.loads(greeting)["msg"] == "connected":
        return
    session = json.loads(greeting)["session"]

    # BUG: only root can call the APIs in all versions up to 11.3-U4.1
    pwdkey = f"{args.user}@{server}"
    password = args.password
    forcePrompt = (password == 'PROMPT')
    if not password or forcePrompt:
        password = keyring.get_password("NAS API", pwdkey)      # check if we have something stashed
        if not password or forcePrompt:
            password = getpass.getpass(f"{pwdkey} password:")   # prompt and safely stash it away for next time
            keyring.set_password("NAS API", pwdkey, password)

    await websocket.send(json.dumps({
        "id": session,
        "msg": "method",
        "method": "auth.login",
        "params": [args.user, password]
        }))
    auth_status = await websocket.recv()
    if args.verbosity >= 3:
        print(f"< {auth_status}")
    
    if not json.loads(auth_status)["result"] == True:
        print (json.loads(auth_status)["error"])
        return None

    return session

async def nas_list_vms(server):
    async with websockets.connect(nas_socketname(server)) as websocket:
        session = await nas_create_session(server, websocket)

        if session:
            # Will print out all your vms and their info, find the id you need
            await websocket.send(json.dumps({
                "id": session,
                "msg": "method",
                "method": "vm.query",
                "params": []
                }))
            query_result = await websocket.recv()
            if args.verbosity >= 3:
                print(f"< {query_result}")
            vm_list = json.loads(query_result)["result"]

            print (f"{'ID':>4} {'Name':12.12} {'PID':>6} {'Description':40.40}")
            for vm in vm_list:
                pid = vm['status']['pid'] or '[none]'
                print (f"{vm['id']:>4} {vm['name']:12.12} {pid:>6} {vm['description']:40.40}")

async def nas_start_vm(server, id_list, overcommit):
    async with websockets.connect(nas_socketname(server)) as websocket:
        session = await nas_create_session(server, websocket)

        if session:
            for id in id_list:
                await websocket.send(json.dumps({
                    "id": session,
                    "msg": "method",
                    "method": "vm.start",
                    "params": [id, {'overcommit': overcommit}]
                    }))
                query_result = await websocket.recv()
                if args.verbosity >= 3:
                    print(f"< {query_result}")
                try:
                    vm_started = json.loads(query_result)["result"]
                    if args.verbosity >= 1:
                        print(vm_started)
                except:
                    errormsg = json.loads(query_result)["error"]["reason"]
                    print(errormsg)
            

async def nas_start_vm(server, id_list):
    async with websockets.connect(nas_socketname(server)) as websocket:
        session = await nas_create_session(server, websocket)

        if session:
            for id in id_list:
                await websocket.send(json.dumps({
                    "id": session,
                    "msg": "method",
                    "method": "vm.stop",
                    "params": [id]
                    }))
                query_result = await websocket.recv()
                if args.verbosity >= 3:
                    print(f"< {query_result}")
                try:
                    vm_stopped = json.loads(query_result)["result"]
                    if args.verbosity >= 1:
                        print(vm_stopped)
                except:
                    errormsg = json.loads(query_result)["error"]["reason"]
                    print(errormsg)
            

async def nas_shutdown_vm(server, id_list):
    async with websockets.connect(nas_socketname(server)) as websocket:
        session = await nas_create_session(server, websocket)

        if session:
            for id in id_list:
                await websocket.send(json.dumps({
                    "id": session,
                    "msg": "method",
                    "method": "vm.status",
                    "params": [id]
                    }))
                query_result = await websocket.recv()
                if args.verbosity >= 3:
                    print(f"< {query_result}")

                try:
                    pid = json.loads(query_result)["result"]["pid"]
                    os.system(f"echo kill -TERM {pid}")
                except:
                    errormsg = json.loads(query_result)["error"]["reason"]
                    print(errormsg)


def cmd_list(args):
    if args.verbosity >= 3:
        print("LIST")
        print (args)
    asyncio.get_event_loop().run_until_complete(nas_list_vms(args.server))

def cmd_start(args):
    if args.verbosity >= 3:
        print("START")
        print (args)
    asyncio.get_event_loop().run_until_complete(nas_start_vm(args.server, args.vm, args.overcommit))

def cmd_stop(args):
    if args.verbosity >= 3:
        print("STOP")
        print (args)
    asyncio.get_event_loop().run_until_complete(nas_stop_vm(args.server, args.vm))

def cmd_shutdown(args):
    if args.verbosity >= 3:
        print("SHUTDOWN")
        print (args)
    asyncio.get_event_loop().run_until_complete(nas_shutdown_vm(args.server, args.vm))

def cmd_default(args):
    if args.verbosity >= 3:
        print("DEFAULT")
        print (args)
    parser.error("invalid arguments")

parser = argparse.ArgumentParser(prog="nasvm",
    description="Manage VM's in a FreeNAS/TrueNAS server", 
    epilog="Passwords are cached in your local OS storage for passwords (e.g., keychain on MacOS)." \
            " You can manage that with the cross platform command 'keyring' using service name 'NAS API'." \
            " Note that in FreeNAS up to 11.3-U4.1 only root can call the API.")
parser.add_argument("-u", "--user", metavar='name', action="store", help="user name for authentication (defaults to root)", default="root")
parser.add_argument("-p", "--password", nargs='?', action="store", const='PROMPT', metavar='pwd', help="password for authentication, prompt if none given, or use cached password otherwise")
parser.add_argument("-s", "--server", metavar='addr', action="store", help="hostname or IP of NAS server (defaults to $NASVM_SERVER)", default=os.environ.get('NASVM_SERVER'))
parser.add_argument("-v", "--verbosity", action="count", default=0, help="control verbosity, multiple increase verbosity up to 3")
parser.set_defaults(func=cmd_default)

subparsers = parser.add_subparsers(title="commands", description="valid commands (see more with nasvm command --help)")

parser_list = subparsers.add_parser('list', aliases=['ls'], help="list configured VMs")
parser_list.set_defaults(func=cmd_list)

parser_start = subparsers.add_parser('start', help="start given VMs")
parser_start.add_argument("vm", metavar="VM", type=int, nargs='+', help="vm identifiers (get with nasvm list)")
parser_start.add_argument("-o", "--overprovision", action="store_true", help="start VM even if not enough free memory available")
parser_start.set_defaults(func=cmd_start)

parser_stop = subparsers.add_parser('stop', help="stops given VMs immediately")
parser_stop.add_argument("vm", metavar="VM", type=int, nargs='+', help="vm identifiers (get with nasvm list)")
parser_stop.set_defaults(func=cmd_stop)

parser_shut = subparsers.add_parser('shutdown', aliases=['shut'], help="attempts to shutdown given VMs")
parser_shut.add_argument("vm", metavar="VM", type=int, nargs='+', help="vm identifiers (get with nasvm list)")
parser_shut.set_defaults(func=cmd_shutdown)

args = parser.parse_args()

if not args.server:
    parser.error("no server given")
args.func(args)
