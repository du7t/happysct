import concurrent.futures

from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse, RedirectResponse
import yaml

from api_libs.logger import Logger, log

import libs.helper as helper
from libs.core import SCTManager, filter_services

logger = Logger()


app = FastAPI(title='HappySCT', version="1.0", description="Manage SCT records")
services_router = APIRouter(tags=["services"])
schemes_router = APIRouter(tags=["schemes"])


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


# Redirect root path to /docs
@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse(url="/docs", status_code=302)


@services_router.get("/update/{env_name}", summary="Add or recreate services config in SCT")
@log(logger)
def update(
    env_name: str,
    force: bool = False,
    only: str = '',
    group: str = '',
    exclude: str = ''
):
    """
    Parameters:
    - `env_name` (str): Name of the target environment
    - `force` (bool, optional): If True - adds new services and recreates existing ones.
    - `only` (str, optional): Services to include in the update
    - `group` (str, optional): Group of services to include in the update by source service
    - `exclude` (str, optional): Services to exclude from the update

    Examples:
    - /update/lab-lem-ams
    - /update/lab-lem-ams?only=ace
    - /update/lab-lem-ams?only=ace&force=1
    - /update/lab-lem-ams?only=ace,pas
    - /update/lab-lem-ams?group=pwr
    - /update/lab-lem-ams?exclude=jws
    """
    sct_manager = SCTManager(env_name)
    services_to_process = filter_services(sct_manager.env_services, only, group, exclude, force)

    result = {
        'force_mode': force,
        'services_to_process': services_to_process,
        'failed': [],
        'added': [],
        'recreated': [],
        'skipped': [],
        'by_service': {}
    }

    def _process_service(service):
        update_result = sct_manager.update(service=service, force=force)
        if not update_result.get("status", False) and 'not present' in update_result.get('message', ''):
            result['skipped'].append(service)
        elif not update_result.get("status", False):
            result['failed'].append(service)
        elif update_result.get("status", True) and not update_result.get("updated", False):
            result['skipped'].append(service)
        elif update_result.get("old_deleted", False):
            result['recreated'].append(service)
        elif update_result.get("updated", True):
            result['added'].append(service)

        result['by_service'][service] = update_result

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for service in services_to_process:
            executor.submit(_process_service, service)

    return result


@schemes_router.get("/update/{env_name}/schemes", summary="Update default deployment schemes")
@log(logger)
def update_schemes(env_name: str):
    sct_manager = SCTManager(env_name)
    schemes_result = sct_manager.update_deployment_schemes()

    return schemes_result


@services_router.get("/show/{env_name}", summary="Show services current config")
@log(logger)
def show(
    env_name: str,
    only: str = '',
    group: str = '',
    exclude: str = ''
):
    sct_manager = SCTManager(env_name)
    services_to_process = filter_services(sct_manager.env_services, only, group, exclude, force=None)

    result = dict()
    for service in services_to_process:
        result[service] = sct_manager.get_current(service)
    return result


@services_router.get("/diff/{env_name}", summary="Difference between current services config and new generated one")
@log(logger)
def diff(
    env_name: str,
    only: str = '',
    group: str = '',
    exclude: str = ''
):
    sct_manager = SCTManager(env_name)
    services_to_process = filter_services(sct_manager.env_services, only, group, exclude, force=True)

    result = {
        'fail': [],
        'add': [],
        'recreate': [],
        'skip': [],
        'by_service': {}
    }

    def _process_service(service):
        diff_result = sct_manager.get_diff(service)
        if not diff_result.get("status", False) and 'not present' in diff_result.get('message', ''):
            result['skip'].append(service)
        elif not diff_result.get("status", False):
            result['fail'].append(service)
        elif not diff_result.get('config_diff', {}):
            result['skip'].append(service)
        elif diff_result.get('config_diff', {}) and service not in sct_manager.env_services:
            result['add'].append(service)
        elif diff_result.get('config_diff', {}) and service in sct_manager.env_services:
            result['recreate'].append(service)

        result['by_service'][service] = diff_result

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for service in services_to_process:
            executor.submit(_process_service, service)

    return result


@app.get("/ops-metadata")
@log(logger)
def ops_metadata():
    stream = open('ops-metadata.yaml', 'r')
    metadata = yaml.safe_load(stream=stream)
    metadata['OPS-METADATA']['communicates_with'] = list()
    metadata['OPS-METADATA']['communicates_with'].append(helper.get_ff('SCT_URL'))

    return metadata


@app.get("/health")
@log(logger)
def health():
    return helper.get_health()


app.include_router(services_router)
app.include_router(schemes_router)
