# HappySCT

## Architecture
HappySCT Lucidchart


## API

- [`Labduction`](http://happysct.mydomain/)

- [`Sandbox`](http://happysct-sandbox.mydomain/)


## CLI install

1. Make sure to fill out `conf/settings.py`

2. Install requirements

    `pip3 install -r requirements.txt`


## CLI usage

- Get help:

    `python happysct.py --help`

- Update services, only missing services will be added:

    `python happysct.py update env-name`

- Update only specific services:

    `python happysct.py update env-name --only ace,rmx`

- Update services group by source service:

    `python happysct.py update env-name --group das`

- Exclude specific services from update:

    `python happysct.py update env-name --exclude ace`

- Update services, add missing services and override current:

    `python happysct.py update env-name --force`

- Update both services and deployment schemes:

    `python happysct.py update env-name --schemes`

- Show current services config:

    `python happysct.py show env-name --only ace`

- Show difference: current services config vs new:

    `python happysct.py diff env-name --only ace`

- Rollout new service on Lab envs manually:

    `python rollout.py --only ndb` 

- Rollout new service on Lab envs manually with override:

    `python rollout.py --only ndb --force` 



## How-tos

#### How to switch from local service to shared and vice versa

1. 
    Switch to shared: undeploy local service from env and remove placeholder
    
    Switch to local: deploy service to env

2. Run `python happysct.py update env-name --force --only service-name`


#### How to add new service to `services.json`

1. Find new service OPS spec in Wiki, get SCT config: deploymentScheme, port, ssl and if specified - location, physicalEnv, group
    
    Example: https://wiki.mydomain/x/FfYDIw


2. Edit `conf/services.json`: copy similar service config, specify fields different from copied service


3. Pay attention to fields location, physicalEnv, address, port,
they are often calculated from ADS variable, like _{SERVER_FQDN}_


4. Address. It contains 4 fields

    The `default` must have a value. Usually it calculated from         variable _{SERVER_FQDN}_, no matter shared or local, but there are some exception, like _{ENV.PLATFORM.PasApiURL}_ in PAS

    The `shared_by_env` can be null. It is for services that have non-fqdn shared address, vip for example, and shared by env. It must have defualt value in it. See CNS, CPX

    The `shared_by_location` can be null. It is for services that shared by location or have one default value for Lab. It must have defualt value in it. See CIN, EEF

    Address can be shared either by env or by location. Not both.

    The `source_service` can be null. It is for services that either were replaced by new service, such as JWS > JWL, TAS > TBR, or for services that depend on main service, see HIT-ADMIN > HIT, Extapi, Intapi > PWR  


5. Commit changes, make sure pipeline completes



## SCT service brief info
Services described in `conf/services.json`.
We use ADS variables for dynamic fields calculation.

#### Required fields:

- serviceName
- serviceVersion
- serviceInterface
- deploymentScheme
- ssl
- address
- port

#### Optional fields, can be null:

- location
- physicalEnv
- group


## Magic button integration

#### Update environment

`python3 happysct.py update env-name`

#### Create environment 

`python3 happysct.py update env-name --schemes --force`


## References

- Task: https://jira.mydomain/browse/ENV-98855

- SCT API: https://wiki.mydomain/display/PLAT/SCT+HTTP+API

- SDI Processing: https://wiki.mydomain/display/PLAT/SDI+Processing

- SDI Storage Scheme: https://wiki.mydomain/display/PLAT/SDI+Storage+Scheme

- SDI Deployment Schemes: https://wiki.mydomain/display/PLAT/SDI+Deployment+Schemes
