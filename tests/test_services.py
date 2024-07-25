import json
import os

from jsonschema import validate, ValidationError


services_file = "services.json"
schema_file = "services_schema.json"
services_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "..", "conf", services_file)
schema_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "conf", schema_file)


def test_json_valid():
    try:
        with open(services_file_path, "r") as f:
            services_conf = json.load(f)
        with open(schema_file_path, "r") as f:
            services_schema = json.load(f)
        validate(instance=services_conf, schema=services_schema)
    except json.JSONDecodeError as error:
        assert False, f'Decode json exception: {error}'
    except ValidationError as error:
        assert False, f'Validation services json by schema exception: {error}'
