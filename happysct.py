"""CLI"""

import concurrent.futures
import fire
import json
import sys

from rich import print as rprint
from rich.progress import track
from rich.table import Table

from libs.core import SCTManager, filter_services
import api_libs.gitup as gitup
from libs.helper import get_ff
from api_libs.logger import Logger, log


logger = Logger()


def pp(s='') -> None:
    """Use rich pretty print"""
    if get_ff('FRIENDLY_PRINT') and get_ff('LOG_LEVEL') in ['ERROR', 'CRITICAL']:
        rprint(s)


def check_args(env_name) -> None:
    if not (isinstance(env_name, str)):
        raise ValueError("Incorrect arguments")


def print_diff_table(add: list, recreate: list, skip: list, fail: list) -> None:
    table = Table(title="Changes summary")
    table.add_column("Change", style="cyan", no_wrap=True)
    table.add_column("Service")
    if add:
        table.add_row("Add", ", ".join(add))
        logger.log.info(f"Add: {add}")
    if recreate:
        table.add_row("Recreate", ", ".join(recreate))
        logger.log.info(f"Recreate: {recreate}")
    if fail:
        table.add_row("Fail", ", ".join(fail))
        logger.log.info(f"Fail: {fail}")
    if skip:
        table.add_row("Skip", ", ".join(skip))
        logger.log.info(f"Skip: {skip}")
    pp(table)


class CLI(object):
    """
    CLI for managing SCT records.

    Run 'happysct.py COMMAND --help' for more information on a command.
    """
    @log(logger)
    def update(self, env_name: str, only='', group='', exclude='', force=False, schemes=False) -> None:
        """
        Add or recreate services and deployment schemes configuration in environment.

        Args:
            env_name: Name of the target environment.
            only: Specify services to include in the update.
            group: Specify group of services to include in the update by source service.
            exclude: Specify services to exclude from the update.
            force: If True, adds new services and recreates existing ones.
            schemes: If True, also updates deployment schemes.
        """
        check_args(env_name)
        sct_manager = SCTManager(env_name)
        if schemes:
            pp("\nProcessing schemes...")
            result = sct_manager.update_deployment_schemes()
            if not result.get("status", False):
                raise RuntimeError("Unable to update deployment schemes")
            pp(f"\nSchemes updated: {result.get('message', [])}")

        if services_to_process := filter_services(sct_manager.env_services, only, group, exclude, force):
            pp(f"\nServices to process: {services_to_process}\n")
            failed, skipped, added, recreated = list(), list(), list(), list()

            for service in track(services_to_process, disable=not (get_ff("PROGRESS_BAR"))):
                update_result = sct_manager.update(service=service, force=force)
                if not update_result.get("status", False) and 'not present' in update_result.get('message', ''):
                    skipped.append(service)
                    pp(f"[bright_blue]{service}[/] - "
                       f"{update_result.get('message', None)}, [gold1]skipped")
                elif not update_result.get("status", False):
                    failed.append(service)
                    pp(f"[bright_blue]{service}[/] - "
                       f"{update_result.get('message', None)}, [red3]failed")
                elif update_result.get("status", True) and not update_result.get("updated", False):
                    skipped.append(service)
                    pp(f"[bright_blue]{service}[/] - "
                       f"{update_result.get('message', None)}, [green4]skipped")
                elif update_result.get("old_deleted", False):
                    recreated.append(service)
                    pp(f"[bright_blue]{service}[/] - [green4]recreated")
                elif update_result.get("updated", True):
                    added.append(service)
                    pp(f"[bright_blue]{service}[/] - [green4]added")

            failed.sort(), skipped.sort(), added.sort(), recreated.sort()

            logger.log.info(f"Completed. Services failed: {failed}, skipped: {skipped}, "
                            f"added: {added}, recreated: {recreated}")
            pp(f"\nCompleted. Services failed: {failed}, skipped: {skipped}, "
               f"added: {added}, recreated: {recreated}")
            if failed:
                raise RuntimeError("Some services failed")
        else:
            pp("\nNo services to process.\n")

    @log(logger)
    def diff(self, env_name: str, only='', group='', exclude='') -> None:
        """
        Show service difference between current config on env and new generated one.
        """
        check_args(env_name)
        sct_manager = SCTManager(env_name)
        services_to_process = filter_services(sct_manager.env_services, only, group, exclude, force=True)
        fail, skip, add, recreate = list(), list(), list(), list()
        pp("Changes - current / new\n")

        def _process_service(service):
            diff_result = sct_manager.get_diff(service=service)
            if not diff_result.get("status", False) and 'not present' in diff_result.get('message', ''):
                skip.append(service)
                pp(f"[bright_blue]{service}[/] - {diff_result.get('message', None)}, skipped")
            elif not diff_result.get("status", False) and diff_result.get("current_config", []):
                fail.append(service)
                pp(f"[bright_blue]{service}[/] - {diff_result.get('message', None)}")
                pp("Current:")
                pp(diff_result.get('current_config', []))
            elif not diff_result.get("status", False):
                fail.append(service)
                pp(f"[bright_blue]{service}[/] - {diff_result.get('message', None)}")
            elif not diff_result.get('config_diff', {}):
                skip.append(service)
            elif diff_result.get('config_diff', {}) and service not in sct_manager.env_services:
                pp(f"[bright_blue]{service}[/] - will be added:"
                   f"\n{json.dumps(diff_result.get('new_config', {}), indent=4)}")
                add.append(service)
            elif diff_result.get('config_diff', {}) and service in sct_manager.env_services:
                pp(f"[bright_blue]{service}[/] - will be recreated:"
                   f"\n{json.dumps(diff_result.get('config_diff', {}), indent=4)}")
                recreate.append(service)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            for service in services_to_process:
                executor.submit(_process_service, service)

        add.sort(), recreate.sort(), skip.sort(), fail.sort()
        pp()
        if fail or add or recreate:
            print_diff_table(add, recreate, skip, fail)
        else:
            pp("No changes.")
            logger.log.info(f"No changes. Skip: {skip}")

    @log(logger)
    def show(self, env_name: str, only='', group='', exclude='') -> None:
        """
        Show service current config on env.
        """
        check_args(env_name)
        sct_manager = SCTManager(env_name)
        services_to_process = filter_services(sct_manager.env_services, only, group, exclude, force=None)
        for service in services_to_process:
            pp(f"[bright_blue]{service}[/]")
            pp(sct_manager.get_current(service))


def main() -> None:
    try:
        if get_ff('GIT_UPDATE'):
            gitup.check()
        cli = CLI()
        fire.Fire(cli)
    except Exception as error:
        logger.log.exception(f'Exception: {error}')
        sys.exit(1)


if __name__ == "__main__":
    main()
