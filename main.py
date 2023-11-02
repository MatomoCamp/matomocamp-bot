import asyncio
import json
import time
from copy import deepcopy
from sys import argv
from typing import Union, Dict

from nio import AsyncClient, RoomResolveAliasResponse, RoomGetStateEventError, \
    RoomGetStateEventResponse, AsyncClientConfig
from nio.store import MatrixStore

from config import homeserver, user_id, moderators, admins
from data import talks
from urls import chat_rooms

client = AsyncClient(homeserver)

try:
    with open("roomIDmapping.json") as f:
        room_mapping: Dict[str, str] = json.load(f)
except FileNotFoundError:
    room_mapping = {}


def safe_room_mapping(mapping: Dict[str, str]):
    with open("roomIDmapping.json", "w") as f:
        json.dump(mapping, f, indent=2)


async def room_alias_to_id(alias: str) -> str:
    if alias in room_mapping:
        return room_mapping[alias]
    resolve_resp: RoomResolveAliasResponse = await client.room_resolve_alias(alias)
    room_id = resolve_resp.room_id
    room_mapping[alias] = room_id
    safe_room_mapping(room_mapping)
    return room_id


async def main():
    if len(argv) > 1:
        single = argv[1]
    else:
        single = None

    with open("credentials.json") as f:
        data = json.load(f)

    config = AsyncClientConfig(store_sync_tokens=False, store=MatrixStore)
    client = AsyncClient(homeserver, user_id, store_path="./tmp/", config=config)

    client.user_id = user_id
    client.device_id = data["device_id"]
    client.access_token = data["access_token"]
    client.load_store()

    print("starting sync")
    await client.sync()
    print("synced")

    for talk in talks:
        if talk.year != 2023:
            continue
        if talk.id not in chat_rooms:
            continue
        if single and chat_rooms[talk.id] != single:
            continue

        room_alias = f"#{chat_rooms[talk.id]}:matomocamp.org"

        room_id = await room_alias_to_id(room_alias)

        print(room_alias)

        room = client.rooms[room_id]
        print(set(room.users.keys()))

        for admin_id in admins:
            if admin_id not in room.users:
                print(f"inviting {admin_id} to {room_alias}")
                resp=await client.room_invite(room_id, admin_id)
                print(resp)
        for moderator_id in moderators:
            if moderator_id not in room.users:
                print(f"{moderator_id} missing in {room_alias}")
                # time.sleep(4)
                print(f"inviting {moderator_id} to {room_alias}")
                await client.room_invite(room_id, moderator_id)

        await apply_permissions(client, room_id)

        if room.topic != talk.topic:
            print("updating topic")
            await client.update_room_topic(room_id, talk.topic)


    await client.close()


async def apply_permissions(client, room_id):
    room = client.rooms[room_id]
    RespType = Union[RoomGetStateEventResponse, RoomGetStateEventError]
    test: RespType = await client.room_get_state_event(room_id, event_type="m.room.power_levels")
    original_content = deepcopy(test.content)

    users: Dict[str, int] = test.content["users"]
    for moderator_id in moderators:
        if moderator_id in room.users:
            users[moderator_id] = 50
    for admin_id in admins:
        if admin_id in room.users:
            users[admin_id] = 100
    content = test.content
    content["users"] = users
    if content != original_content:
        print("permissions changed")
        print(original_content["users"])
        print(users)
        resp = await client.room_put_state(
            room_id,
            event_type="m.room.power_levels",
            content=content
        )


asyncio.new_event_loop().run_until_complete(main())
