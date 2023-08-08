#!/usr/bin/env python3
import os
import mautrix
import yaml
import asyncio
from mautrix.client import ClientAPI
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import re
from mautrix.types import PaginationDirection
from mcipc.rcon.je import Biome, Client
import mcipc
import datetime

async def loginToMatrix(matrix, roomToBridge, userId):
    await matrix.whoami()
    roomJoined = await matrix.get_joined_rooms()
    if roomToBridge in roomJoined:
        print("[Info] Room Joined")
    else:
        print("Joining room")
        matrix.join_room_by_id(roomToBridge)

async def sendMatrixMessage(message, roomToBridge, matrix):
    messageDict = {
        "body": message,
        "msgtype": "m.text"
    }
    print("[Info] Attempting to send message:", message)
    await matrix.send_message(roomToBridge, messageDict)

async def main():
    with open("config.yaml", 'r') as config_file:
        configData = yaml.safe_load(config_file)

    matrixToken = configData["token"]
    userId = configData["user"]
    baseUrl = configData["base_url"]
    roomToBridge = configData["roomToBridge"]
    matrix = ClientAPI(userId, base_url=baseUrl, token=matrixToken)
    mcPath = configData["serverPath"]
    matrix = ClientAPI(userId, base_url=baseUrl, token=matrixToken)
    rconIp = configData["rconAddress"]
    rconPort = configData["rconPort"]
    rconSecret = configData["rconSecret"]
    unit = configData["serverUnit"]

    await loginToMatrix(matrix, roomToBridge, userId)
    
    print("[Info] Monitoring")

    lastLine = None
    matrixLastMessageStore = None  # Initialize the storage variable

    while True:
        tail_command = "journalctl -eu" + unit + " -n 1 | tail -n 1"
        newLine = subprocess.getoutput(tail_command).strip()
        paginated_messages = await matrix.get_messages(roomToBridge, direction=PaginationDirection.BACKWARD, limit=1)
        if paginated_messages.events:
            matrixLastMessage = paginated_messages.events[0].content.body

            if matrixLastMessageStore is None:
                matrixLastMessageStore = matrixLastMessage  # Store the first message
            elif matrixLastMessage != matrixLastMessageStore:
                matrixLastMessageStore = matrixLastMessage
                print("[Info] New message from Matrix:", matrixLastMessage)
                if "[Minecraft]" in matrixLastMessage:
                    print("Looks like this message is from Minecraft")
                else:
                    messagePending = "[Matrix]: " + matrixLastMessage
                    print("Attempting to send message:", messagePending)
                    with Client(rconIp, rconPort, passwd=rconSecret) as client:
                        listPlayer = client.list(uuids=False)

                    if "online=0" in str(listPlayer):
                        print("[Info] Oops! There isn't anyone on the server!")
                    else:
                        with Client(rconIp, rconPort, passwd=rconSecret) as client:
                            say = client.tell(player="@a", message=messagePending)

                        print(say)

        if newLine:
            if lastLine == None:
                lastLine = newLine
            if newLine != lastLine:
                lastLine = newLine
                print("[Info] Found Chat:", lastLine)
                if "[Matrix]" in newLine:
                    print("Seems that this message is from Matrix")
                else:
                    if "<" in newLine:
                        print("Detected player message")
                        message = lastLine
                        messagePrefixed = "[Minecraft]: " + message
                        print("Attempting to send", message)
                        await sendMatrixMessage(messagePrefixed, roomToBridge, matrix)

        await asyncio.sleep(0.6)

if __name__ == "__main__":
    asyncio.run(main())
