import re
from functools import lru_cache

from generated.job_pb2 import JobResponse


@lru_cache(maxsize=100)
def camel_to_snake(name):
    # Converts "ScheduleResponse" → "schedule_response"
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

@lru_cache(maxsize=100)
def is_oneof_field_exist(field_name):
    return any(field.name == field_name for field in JobResponse.DESCRIPTOR.oneofs_by_name["kind"].fields)


def wrap_in_job_update_response(response) -> JobResponse:
    expected_field = camel_to_snake(response.DESCRIPTOR.name)  # Get snake_case field name
    if is_oneof_field_exist(expected_field):
        outer_response = JobResponse()
        getattr(outer_response, expected_field).CopyFrom(response)
        return outer_response

    raise ValueError(f"No oneof field named '{expected_field}' for type {response.DESCRIPTOR.name}")

