from typing import Dict

from pydantic import ValidationError


def validate_dict_response(response: Dict, schema):
    try:
        schema(**response)
        return True
    except ValidationError as e:
        print(e)
        return False
