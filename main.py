import os
import mautrix
import yaml
import asyncio
from mautrix.client import ClientAPI
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import re

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
    if "serverPath" in os.environ:
        mcPath = os.environ["serverPath"]
        print("serverPath identified @", mcPath)
    else:
        print("Did you set serverPath?")
        os.abort()

    with open("config.yaml", 'r') as config_file:
        configData = yaml.safe_load(config_file)

    matrixToken = configData["token"]
    userId = configData["user"]
    baseUrl = configData["base_url"]
    roomToBridge = configData["roomToBridge"]
    matrix = ClientAPI(userId, base_url=baseUrl, token=matrixToken)

    await loginToMatrix(matrix, roomToBridge, userId)
    monitorFile = os.path.join(mcPath, "logs", "latest.log")
    print("[Info] Monitoring", monitorFile)

    lastLine = None

    while True:
        tail_command = f"tail -n 1 {monitorFile} | grep Chat"
        newLine = subprocess.getoutput(tail_command).strip()

        if newLine:
            if newLine != lastLine:
                lastLine = newLine
                print("[Info] Found 'Chat' line:", lastLine)
                message = re.sub(r'^\[\d{2}:\d{2}:\d{2}\] \[.*\]: \[Not Secure\] ', '', lastLine)
                print("Attempting to send", message)
                await sendMatrixMessage(message, roomToBridge, matrix)

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
)
