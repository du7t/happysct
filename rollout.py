"""Run services update to Lab envs"""

import os
import sys

import fire
import requests

from happysct import CLI, pp
from libs.helper import get_ff, load_json
from api_libs.logger import Logger


logger = Logger()


def get_environments_list(file: str = None) -> list:
    if file:
        with open(file, 'r') as f:
            return [line.strip() for line in f if line.strip()]

    r = requests.get(get_ff("ENVS_URL"))
    r.raise_for_status()
    lab_envs = r.json()

    blacklist_envs_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "conf", "blacklist_envs.json")
    blacklist_envs = load_json(blacklist_envs_file_path)

    for group in blacklist_envs.get("GROUPS", []):
        lab_envs.pop(group, None)

    environments_list = [env for env_group in lab_envs for env in lab_envs[env_group] if
                         env not in blacklist_envs.get("ENVS", [])]
    return environments_list


def rollout(only='', force=False, custom_env_list_file: str = None) -> None:
    cli = CLI()
    environments_list = get_environments_list(file=custom_env_list_file)

    completed_environments = list()
    failed_environments = list()

    for env in environments_list:
        pp(f"\n{env}")
        logger.log.info(env)
        try:
            cli.update(env_name=env, only=only, force=force)
            completed_environments.append(env)
        except Exception as error:
            logger.log.error(f'Exception: {error}')
            failed_environments.append(env)

    logger.log.info(f"Failed envs - {len(failed_environments)}: {failed_environments}")
    logger.log.info(f"Completed envs - {len(completed_environments)}: {completed_environments}")

    if failed_environments:
        sys.exit(1)


def main() -> None:
    fire.Fire(rollout)


if __name__ == "__main__":
    main()
