import asyncio
import getpass
import json

from nio import AsyncClient, LoginResponse

from config import *


async def main():
    client = AsyncClient(homeserver, user_id)

    pw = getpass.getpass()

    resp = await client.login(pw, device_name=devicename)
    print(resp)
    if isinstance(resp, LoginResponse):
        with open("credentials.json", "w") as f:
            json.dump({
                "homeserver": homeserver,
                "user_id": resp.user_id,
                "device_id": resp.device_id,
                "access_token": resp.access_token,
            }, f)
    await client.close()


asyncio.new_event_loop().run_until_complete(main())
