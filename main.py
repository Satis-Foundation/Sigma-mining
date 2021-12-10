import asyncio
import json

from satis_auth import SatisAuth
from sigma_mining import SigmaMining


def private_key_warning():
    """
    show the warning statement to the user and ask them to input the private key
    """

    print("This software will not save your private key")
    PRIVATE_KEY = input("please input your private key here: ")
    return PRIVATE_KEY


def read_config_file():
    """
    read the config file and get all user defined variables
    """
    with open("config.json", "r") as f:
        json_config = json.load(f)
    return json_config


def init_connector(json_config):
    """
    initialize the SATIS connector
    """
    PRIVATE_KEY = private_key_warning()
    AUTH = SatisAuth(PRIVATE_KEY)
    return SigmaMining.initializer(AUTH, json_config)


def init():
    json_config = read_config_file()
    SM = init_connector(json_config)
    SM.apply_config_setting()
    return SM, json_config


async def periodic_clean_up_position(SM, MAX_LIVE_POSITION_TIME):
    while True:
        SM.exit_all_positions()
        await asyncio.sleep(MAX_LIVE_POSITION_TIME)


async def sigma_mining(SM, UPDATE_DELAY):
    while True:
        SM.order_placing()
        SM.get_reward_amount()
        await asyncio.sleep(UPDATE_DELAY)


def main():
    print("initialization")
    SM, json_config = init()
    MAX_LIVE_POSITION_TIME = float(json_config["MAX_LIVE_POSITION_TIME"])
    UPDATE_DELAY = SM.min_update_delay(float(json_config["UPDATE_DELAY"]))

    print("start")
    loop = asyncio.get_event_loop()
    loop.create_task(periodic_clean_up_position(SM, MAX_LIVE_POSITION_TIME))
    loop.create_task(sigma_mining(SM, UPDATE_DELAY))
    loop.run_forever()


if __name__ == "__main__":
    main()
