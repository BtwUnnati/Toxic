import asyncio
import importlib

from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall

import config
from Toxic import LOGGER, app, userbot
from Toxic.core.call import Dev
from Toxic.misc import sudo
from Toxic.plugins import ALL_MODULES
from Toxic.utils.database import get_banned_users, get_gbanned
from config import BANNED_USERS


async def init():
    if (
        not config.STRING1
        and not config.STRING2
        and not config.STRING3
        and not config.STRING4
        and not config.STRING5
    ):
        LOGGER(__name__).error("Assistant client variables not defined, exiting...")
        exit()
    await sudo()
    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except:
        pass
    await app.start()
    for all_module in ALL_MODULES:
        importlib.import_module("Toxic.plugins" + all_module)
    LOGGER("Toxic.plugins").info("Successfully Imported Modules...")
    await userbot.start()
    await Dev.start()
    try:
        await Dev.stream_call("https://te.legra.ph/file/29f784eb49d230ab62e9e.mp4")
    except NoActiveGroupCall:
        LOGGER("Toxic").error(
            "Please turn on the videochat of your log group\channel.\n\nStopping Bot..."
        )
        exit()
    except:
        pass
    await Dev.decorators()
    LOGGER("Toxic").info(
        "\x54\x6f\x78\x69\x63\x20\x42\x6f\x74\x20\x53\x74\x61\x72\x74\x65\x64\x20\x53\x75\x63\x63\x65\x73\x73\x66\x75\x6c\x6c\x79\x2e"
    )
    await idle()
    await app.stop()
    await userbot.stop()
    LOGGER("Toxic").info("Stopping Toxic Bot...")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(init())
