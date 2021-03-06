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

# TODO: this is hardcoded to version 1 of the protocol so it works with TrueNAS 11.3

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

async def __call_method(websocket, sessionID, methodname, params):
    await websocket.send(json.dumps({
        "id": sessionID,
        "msg": "method",
        "method": methodname,
        "params": params
        }))
    query_result = await websocket.recv()
    if args.verbosity >= 3:
        print(f"< {query_result}")
    
    try:
        call_result = json.loads(query_result)["result"]
        return call_result
    except:
        print(f"{PROGNAME}: {methodname} failed")
        errormsg = json.loads(query_result)["error"]["reason"]
        print(f"{PROGNAME}: {errormsg}")
        return None


async def nas_list_vms(server):
    async with websockets.connect(nas_socketname(server)) as websocket:
        session = await nas_create_session(server, websocket)

        if not session:
            return

        # Will print out all your vms and their info, find the id you need
        vm_list = await __call_method(websocket, session, "vm.query", [])

        print (f"{'ID':>4} {'Name':12.12} {'PID':>6} {'Description':40.40}")
        for vm in vm_list:
            pid = vm['status']['pid'] or '[none]'
            print (f"{vm['id']:>4} {vm['name']:12.12} {pid:>6} {vm['description']:40.40}")

async def nas_start_vm(server, id_list, overcommit):
    async with websockets.connect(nas_socketname(server)) as websocket:
        session = await nas_create_session(server, websocket)

        if not session:
            return

        for id in id_list:
            vm_started = await __call_method(websocket, session, "vm.start", [id, {'overcommit': overcommit}])
            if vm_started:
                if args.verbosity >= 1:
                    print(f"{PROGNAME}: {vm_started}")
            

async def nas_restart_vm(server, id_list):
    async with websockets.connect(nas_socketname(server)) as websocket:
        session = await nas_create_session(server, websocket)

        if not session:
            return

        if not args.force:
            print(f"{PROGNAME}: operation on {server} ignored, use -f to force")
            return 

        for id in id_list:
            vm_restarted = await __call_method(websocket, session, "vm.restart", [id])
            if vm_restarted:
                if args.verbosity >= 1:
                    print(f"{PROGNAME}: {vm_restarted}")
            

async def nas_halt_vm(server, id_list):
    async with websockets.connect(nas_socketname(server)) as websocket:
        session = await nas_create_session(server, websocket)

        if not session:
            return

        if not args.force:
            print(f"{PROGNAME}: operation on {server} ignored, use -f to force")
            return 

        for id in id_list:
            vm_halted = await __call_method(websocket, session, "vm.stop", [id])
            if vm_halted:
                if args.verbosity >= 1:
                    print(f"{PROGNAME}: {vm_halted}")
           

async def nas_shutdown_vm(server, id_list):
    async with websockets.connect(nas_socketname(server)) as websocket:
        session = await nas_create_session(server, websocket)

        if not session:
            return

        for id in id_list:
            vm_status = await __call_method(websocket, session, "vm.status", [id])
            if vm_status:
                pid = vm_status["pid"]
                # BUG: this only works on the local server, need to find a way to ssh this overor use a different protocol command
                if os.system(f"echo kill -TERM {pid}") != 0:
                    print(f"{PROGNAME}: vm shutdown failed (signaling {pid})")


async def nas_get_vm_vnc (server, id_list):
    async with websockets.connect(nas_socketname(server)) as websocket:
        session = await nas_create_session(server, websocket)

        if not session:
            return

        if not args.vncport and not args.vncurl:
            print (f"{'ID':>4} {'Port':>6} {'Resolution':10} {'URL'}")

        for id in id_list:
            vnc_list = await __call_method(websocket, session, "vm.get_vnc", [id])
            if vnc_list:
                if args.verbosity >= 1:
                    print(f"{PROGNAME}: {vnc_list}")

            vnc_url_list = await __call_method(websocket, session, "vm.get_vnc_web", [id])
            if vnc_url_list:
                if args.verbosity >= 1:
                    print(f"{PROGNAME}: {vnc_url_list}")

            vnc_port = vnc_list[0]['vnc_port']
            vnc_url = vnc_url_list[0]
            if args.vncport:
                print (vnc_port)
            elif args.vncurl:
                print (vnc_url)
            else:
                print (f"{id:>4} {vnc_port:>6} {vnc_list[0]['vnc_resolution']:10.10} {vnc_url}")


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

def cmd_restart(args):
    if args.verbosity >= 3:
        print("RESTART")
        print (args)
    asyncio.get_event_loop().run_until_complete(nas_restart_vm(args.server, args.vm))

def cmd_halt(args):
    if args.verbosity >= 3:
        print("HALT")
        print (args)
    asyncio.get_event_loop().run_until_complete(nas_halt_vm(args.server, args.vm))

def cmd_shutdown(args):
    if args.verbosity >= 3:
        print("SHUTDOWN")
        print (args)
    asyncio.get_event_loop().run_until_complete(nas_shutdown_vm(args.server, args.vm))

def cmd_vnc(args):
    if args.verbosity >= 3:
        print("VNC")
        print (args)
    asyncio.get_event_loop().run_until_complete(nas_get_vm_vnc(args.server, args.vm))

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
parser.add_argument("-f", "--force", action="store_true", help="force command to take destructive action", default=False)
parser.add_argument("-v", "--verbosity", action="count", default=0, help="control verbosity, multiple increase verbosity up to 3")
parser.set_defaults(func=cmd_default)

subparsers = parser.add_subparsers(title="commands", description=f"valid commands (see more with {PROGNAME} command --help)")

parser_list = subparsers.add_parser('list', aliases=['ls'], help="list configured VMs")
parser_list.set_defaults(func=cmd_list)

parser_start = subparsers.add_parser('start', help="start given VMs")
parser_start.add_argument("vm", metavar="VM", type=int, nargs='+', help=f"vm identifiers (get with {PROGNAME} list)")
parser_start.add_argument("-o", "--overprovision", action="store_true", default=False, help="start VM even if not enough free memory available")
parser_start.set_defaults(func=cmd_start)

parser_halt = subparsers.add_parser('restart', help="halts given VMs immediately and restarts them")
parser_halt.add_argument("vm", metavar="VM", type=int, nargs='+', help=f"vm identifiers (get with {PROGNAME} list)")
parser_halt.set_defaults(func=cmd_restart)

parser_halt = subparsers.add_parser('halt', help="halts given VMs immediately")
parser_halt.add_argument("vm", metavar="VM", type=int, nargs='+', help=f"vm identifiers (get with {PROGNAME} list)")
parser_halt.set_defaults(func=cmd_halt)

parser_shut = subparsers.add_parser('shutdown', aliases=['shut'], help="attempts to shutdown given VMs")
parser_shut.add_argument("vm", metavar="VM", type=int, nargs='+', help=f"vm identifiers (get with {PROGNAME} list)")
parser_shut.set_defaults(func=cmd_shutdown)

parser_vnc = subparsers.add_parser('vnc', help="list VNC attributes of given VMs")
parser_vnc_group = parser_vnc.add_mutually_exclusive_group()
parser_vnc_group.add_argument("--url", dest='vncurl', action="store_true", help="print only the url")
parser_vnc_group.add_argument("--port", dest='vncport', action="store_true", help="print only the port number")
parser_vnc.add_argument("vm", metavar="VM", type=int, nargs='+', help=f"vm identifiers (get with {PROGNAME} list)")
parser_vnc.set_defaults(func=cmd_vnc)

args = parser.parse_args()

if not args.server:
    parser.error("no server given")

try:
    args.func(args)
except:
    print(f"{PROGNAME}: error: could not complete request")     # comment out try/except to make debugging easier

# def main():
#     print("Hello World!")

# if __name__ == "__main__":
#     main()
    
