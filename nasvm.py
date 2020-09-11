#!/usr/bin/env python3
import asyncio
import websockets
import json
import keyring
import getpass
import os

debug=False

def nas_socketname(server):
    return f"ws://{server}/websocket"

# creates an authenticated API session, returns the ID for further calls
async def nas_create_session(websocket):
    await websocket.send(json.dumps({
        "msg": "connect",
        "version": "1",
        "support": ["1"]
        }))
    greeting = await websocket.recv()
    if debug:
        print(f"< {greeting}")

    if not json.loads(greeting)["msg"] == "connected":
        return
    session = json.loads(greeting)["session"]

    # BUG: only root can call the APIs in all versions up to 11.3-U4.1
    username = "root"
    password = keyring.get_password("NAS API", username)
    if password == None:
        password = getpass.getpass()    # prompt and safely stash it away for next time
        keyring.set_password("NAS API", "root", password)

    await websocket.send(json.dumps({
        "id": session,
        "msg": "method",
        "method": "auth.login",
        "params": [username, password]
        }))
    auth_status = await websocket.recv()
    if debug:
        print(f"< {auth_status}")
    
    if not json.loads(auth_status)["result"] == True:
        print (json.loads(auth_status)["error"])
        return None

    return session

async def nas_list_vms(server):
    async with websockets.connect(nas_socketname(server)) as websocket:
        session = await nas_create_session(websocket)

        if session:
            # Will print out all your vms and their info, find the id you need
            await websocket.send(json.dumps({
                "id": session,
                "msg": "method",
                "method": "vm.query",
                "params": []
                }))
            query_result = await websocket.recv()
            if debug:
                print(f"< {query_result}")
            vm_list = json.loads(query_result)["result"]
            # print (vm_list)
            print (f"{'ID':>4} {'Name':12.12} {'PID':>6} {'Description':40.40}")
            for vm in vm_list:
                pid = vm['status']['pid'] or '[none]'
                print (f"{vm['id']:>4} {vm['name']:12.12} {pid:>6} {vm['description']:40.40}")

async def nas_start_vm(server, id):
    async with websockets.connect(nas_socketname(server)) as websocket:
        session = await nas_create_session(websocket)

        if session:
            # Will print out all your vms and their info, find the id you need
            await websocket.send(json.dumps({
                "id": session,
                "msg": "method",
                "method": "vm.start",
                "params": [id]
                }))
            query_result = await websocket.recv()
            if debug:
                print(f"< {query_result}")
            try:
                vm_started = json.loads(query_result)["result"]
                print(vm_started)
            except:
                errormsg = json.loads(query_result)["error"]["reason"]
                print(errormsg)
            

async def nas_shutdown_vm(server, id):
    async with websockets.connect(nas_socketname(server)) as websocket:
        session = await nas_create_session(websocket)

        if session:
            await websocket.send(json.dumps({
                "id": session,
                "msg": "method",
                "method": "vm.status",
                "params": [id]
                }))
            query_result = await websocket.recv()
            if debug:
                print(f"< {query_result}")

            try:
                pid = json.loads(query_result)["result"]["pid"]
                os.system(f"echo kill -TERM {pid}")
            except:
                errormsg = json.loads(query_result)["error"]["reason"]
                print(errormsg)


asyncio.get_event_loop().run_until_complete(nas_list_vms("urca"))

#asyncio.get_event_loop().run_until_complete(nas_start_vm("urca", 1))

#asyncio.get_event_loop().run_until_complete(nas_shutdown_vm("urca", 1))
