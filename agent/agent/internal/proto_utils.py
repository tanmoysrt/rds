import dataclasses
import importlib
import importlib.util
import inspect
import os
from functools import lru_cache

from google.protobuf import symbol_database
from google.protobuf.message import Message

from agent.internal.config import ServerConfig

sym_db = symbol_database.Default()

@dataclasses.dataclass
class ServiceImplInfo:
    class_obj: type
    adapter: callable
    methods: set[str]
    method_response_types: dict[str, str]

def is_valid_rpc_method(func) -> bool:
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    if len(params) != 3:
        return False

    return (
        params[0].name == 'self' and
        params[1].name == 'request' and
        params[2].name == 'context'
    )

@lru_cache(maxsize=1)
def discover_protobuf_messages() -> dict[str, type]:
    registry = {}
    config = ServerConfig()
    for file in os.listdir(os.path.join(config._base_path, config.generated_protobuf_dir)):
        if not file.endswith("_pb2.py"):
            continue

        module_name = file[:-3]
        module = importlib.import_module(f"{config.generated_protobuf_dir}.{module_name}")

        for name, obj in inspect.getmembers(module):
            if not (inspect.isclass(obj) and issubclass(obj, Message)):
                continue

            class_full_name = f"{obj.__module__}.{obj.__name__}"
            if class_full_name in registry:
                raise ValueError(f"Duplicate protobuf message class found: {class_full_name}")

            registry[class_full_name] = obj

    return registry

@lru_cache(maxsize=1)
def discover_protobuf_messages_with_meta() -> set[str]:
    registry = discover_protobuf_messages()
    messages_with_meta = set()
    for message_name, message_class in registry.items():

        if any(field.name == "meta" for field in message_class.DESCRIPTOR.fields):
            messages_with_meta.add(message_name)
    return messages_with_meta

@lru_cache(maxsize=1)
def discover_grpc_service_impls() -> dict[str, ServiceImplInfo]:
    registry = {}
    config = ServerConfig()
    for file in os.listdir(os.path.join(config._base_path, config.service_impl_dir)):
        if not file.endswith(".py"):
            continue
        module_name = f"{config.service_impl_dir.replace('/', '.')}.{file[:-3]}"
        module = importlib.import_module(module_name)

        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and any(x.__name__.endswith("Servicer") for x in obj.__bases__):
                # Fetch all the methods
                methods = set(
                    [
                        method_name
                        for method_name, method_obj in inspect.getmembers(obj, inspect.isfunction)
                        if method_obj.__qualname__.startswith(obj.__name__ + ".")
                        and not method_name.startswith("_")
                        and is_valid_rpc_method(method_obj)
                    ]
                )

                # Find adapter
                base_class = [
                    base_class for base_class in obj.__bases__ if base_class.__name__.endswith("Servicer")
                ][0]
                base_class_module_dotted_path = (
                    os.path.relpath(inspect.getfile(base_class), config._base_path)
                    .replace("/", ".")
                    .replace(".py", "")
                )
                base_class_module = importlib.import_module(base_class_module_dotted_path)
                adapters = [
                    method_obj
                    for method_name, method_obj in inspect.getmembers(base_class_module)
                    if inspect.isfunction(method_obj)
                    and method_name == f"add_{base_class.__name__}_to_server"
                ]
                if not adapters:
                    raise ValueError(
                        f"No adapter found for {base_class.__name__} in {base_class_module_dotted_path}"
                    )

                # Fetch return type of each method
                method_response_types = {}
                base_class_descriptor = importlib.import_module(base_class_module_dotted_path.rstrip("_grpc")).DESCRIPTOR
                for method_name, method_descriptor in base_class_descriptor.services_by_name[
                    obj.__name__
                ].methods_by_name.items():
                    if method_name not in methods:
                        raise ValueError(
                            f"Method {method_name} not found in {obj.__name__}. But found in descriptor. Looks like missing implementation."
                        )

                    message_class = sym_db.GetSymbol(method_descriptor.output_type.full_name)
                    method_response_types[method_name] = (
                        f"{message_class.__module__}.{message_class.__name__}"
                    )

                registry[f"{base_class_descriptor.package}.{obj.__name__}"] = ServiceImplInfo(
                    class_obj=obj,
                    adapter=adapters[0],
                    methods=methods,
                    method_response_types=method_response_types,
                )
    return registry


def get_service_method(service_name: str, method_name: str) -> callable:
    service_impls = discover_grpc_service_impls()
    if service_name not in service_impls:
        raise ValueError(f"Service {service_name} not found")

    service_info = service_impls[service_name]
    if method_name not in service_info.methods:
        raise ValueError(f"Method {method_name} not found in service {service_name}")

    return getattr(service_info.class_obj(), method_name)
