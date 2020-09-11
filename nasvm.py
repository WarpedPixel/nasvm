#!/usr/bin/env python3
import asyncio
import websockets
import json
import keyring
import getpass

debug=False

async def start_vm():
    # Set you ip or hostname
    uri = "ws://urca/websocket"
    async with websockets.connect(uri) as websocket:
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

        # BUG: only root can call the APIs in 11.3-U4.1
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
            return

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

        # # List status of vm #1
        # await websocket.send(json.dumps({
        #     "id": session,
        #     "msg": "method",
        #     "method": "vm.status",
        #     "params": [1]
        #     }))
        # query_result = await websocket.recv()
        # if debug:
        #     print(f"< {query_result}")

asyncio.get_event_loop().run_until_complete(start_vm())
