#!/usr/bin/env python3
import asyncio
import websockets
import json

# TODO: hardcoded to always start vm #1

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
        print(f"< {greeting}")
        session = json.loads(greeting)["session"]

        # BUG: only root can call the APIs in 11.3-U4.1
        await websocket.send(json.dumps({
            "id": session,
            "msg": "method",
            "method": "auth.login",
            "params": ["root",""]
            }))

        auth_status = await websocket.recv()
        print(f"< {auth_status}")

        # Will print out all your vms and their info, find the id you need
        await websocket.send(json.dumps({
            "id": session,
            "msg": "method",
            "method": "vm.query",
            "params": []
            }))

        query_result = await websocket.recv()
        print(f"< {query_result}")

        # List status of vm #1
        await websocket.send(json.dumps({
            "id": session,
            "msg": "method",
            "method": "vm.status",
            "params": [1]
            }))

        query_result = await websocket.recv()
        print(f"< {query_result}")

asyncio.get_event_loop().run_until_complete(start_vm())
