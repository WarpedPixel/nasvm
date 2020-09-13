#!/usr/bin/env python3
import asyncio
import websockets
import json
import keyring
import getpass
import os
import sys
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

    def prompt_password():
        p = getpass.getpass(f"{pwdkey} password:")  # prompt 
        if not p:
            parser.error("missing password")
        return p

    if args.prompt_password:
        password = prompt_password()
    elif args.password:
        password = args.password
    else:
        password = keyring.get_password("NAS API", pwdkey)      # check if we have something stashed
        if not password:
            password = prompt_password()

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
        print (f"{PROGNAME}: authentication failed")
        return None

    # safely stash it away, if password was successfully authenticated
    keyring.set_password("NAS API", pwdkey, password)

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
                        print(f"{PROGNAME}: {vm_started}")
                except:
                    print(f"{PROGNAME}: vm start failed")
                    errormsg = json.loads(query_result)["error"]["reason"]
                    print(f"{PROGNAME}: {errormsg}")
            

async def nas_stop_vm(server, id_list):
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
                        print(f"{PROGNAME}: {vm_stopped}")
                except:
                    print(f"{PROGNAME}: vm stop failed")
                    errormsg = json.loads(query_result)["error"]["reason"]
                    print(f"{PROGNAME}: {errormsg}")
            

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
                except:
                    print(f"{PROGNAME}: vm shutdown failed")
                    errormsg = json.loads(query_result)["error"]["reason"]
                    print(f"{PROGNAME}: {errormsg}")
                finally:
                    if os.system(f"kill -TERM {pid}") != 0:
                        print(f"{PROGNAME}: vm shutdown failed (signaling {pid})")



def cmd_list(args):
    if args.verbosity >= 3:
        print("LIST")
        print (args)
    asyncio.get_event_loop().run_until_complete(nas_list_vms(args.server))

def cmd_start(args):
    if args.verbosity >= 3:
        print("START")
        print (args)
    asyncio.get_event_loop().run_until_complete(nas_start_vm(args.server, args.vm, args.overprovision))

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

PROGNAME,_ = os.path.splitext (sys.argv[0])
parser = argparse.ArgumentParser(prog=PROGNAME,
    description="Manage VM's in a FreeNAS/TrueNAS server", 
    epilog="Passwords are cached in your local OS storage for passwords (e.g., keychain on MacOS)." \
            " You can manage that with the cross platform command 'keyring' using service name 'NAS API'." \
            " Note that in FreeNAS up to 11.3-U4.1 only root can call the API.")
parser.add_argument("-u", "--user", metavar='name', action="store", help="user name for authentication (defaults to root)", default="root")
parser_pwd_group = parser.add_mutually_exclusive_group()
parser_pwd_group.add_argument("-p", "--password", action="store", metavar='pwd', 
    help="optional password for authentication (defaults to cached password). Prompts if none available, successful password is cached.")
parser_pwd_group.add_argument("-P", "--prompt-password", action="store_true", help="force prompt for authentication password")
parser.add_argument("-s", "--server", metavar='addr', action="store", help="hostname or IP of NAS server (defaults to $NASVM_SERVER)", default=os.environ.get('NASVM_SERVER'))
parser.add_argument("-v", "--verbosity", action="count", default=0, help="control verbosity, multiple increase verbosity up to 3")
parser.set_defaults(func=cmd_default)

subparsers = parser.add_subparsers(title="commands", description=f"valid commands (see more with {PROGNAME} command --help)")

parser_list = subparsers.add_parser('list', aliases=['ls'], help="list configured VMs")
parser_list.set_defaults(func=cmd_list)

parser_start = subparsers.add_parser('start', help="start given VMs")
parser_start.add_argument("vm", metavar="VM", type=int, nargs='+', help=f"vm identifiers (get with {PROGNAME} list)")
parser_start.add_argument("-o", "--overprovision", action="store_true", default=False, help="start VM even if not enough free memory available")
parser_start.set_defaults(func=cmd_start)

parser_stop = subparsers.add_parser('stop', help="stops given VMs immediately")
parser_stop.add_argument("vm", metavar="VM", type=int, nargs='+', help=f"vm identifiers (get with {PROGNAME} list)")
parser_stop.set_defaults(func=cmd_stop)

parser_shut = subparsers.add_parser('shutdown', aliases=['shut'], help="attempts to shutdown given VMs")
parser_shut.add_argument("vm", metavar="VM", type=int, nargs='+', help=f"vm identifiers (get with {PROGNAME} list)")
parser_shut.set_defaults(func=cmd_shutdown)

args = parser.parse_args()

if not args.server:
    parser.error("no server given")
args.func(args)

# def main():
#     print("Hello World!")

# if __name__ == "__main__":
#     main()
    
