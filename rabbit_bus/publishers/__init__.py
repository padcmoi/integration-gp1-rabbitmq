"""One module per publisher. A module exposing NAMESPACE, QUEUES (1..N queue
names) and run(args) publishes run\x27s return to each of those queues in direct
mode; drop a new publisher here and restart the service. An optional ARGS dict
({name: example value}) declares the arguments the namespace expects."""

import importlib
import pkgutil

REGISTRY = {}

for module_info in pkgutil.iter_modules(__path__):
    module = importlib.import_module(f"{__name__}.{module_info.name}")
    namespace = getattr(module, "NAMESPACE", None)
    queues = getattr(module, "QUEUES", None)
    run = getattr(module, "run", None)
    declared = getattr(module, "ARGS", {})
    if (
        isinstance(namespace, str)
        and namespace
        and isinstance(queues, (list, tuple))
        and queues
        and all(isinstance(queue, str) and queue for queue in queues)
        and callable(run)
    ):
        REGISTRY[namespace] = {"queues": list(queues), "run": run, "args": declared if isinstance(declared, dict) else {}}
