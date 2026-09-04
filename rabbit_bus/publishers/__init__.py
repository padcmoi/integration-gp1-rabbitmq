"""Publishers, organised like the consumers.

publishers/_global/     free-standing publishers, NAMESPACE declared, triggered
                        by a message naming them (answered 202 Accepted)
publishers/<metier>/    the MIRROR of a consumer verb: when the consumer of the
                        same namespace succeeds, the bus publishes this file's
                        message to its QUEUES, fire-and-forget. Only the five
                        verbs get/post/put/patch/delete are allowed and
                        NAMESPACE must match the path, as on the consumer side.

Every module declares QUEUES (1..N destination queue names, direct mode) and
run(...) building the message. Files starting with "_" are helpers and never
registered. A file that breaks a rule is refused with an error in the journal.
"""

import importlib
import logging
import pkgutil

# Re-exported so the two publishing paths force the shape without reaching into
# a private module of this package.
from ._event import normalize  # noqa: F401

logger = logging.getLogger("bus.registry")

ALLOWED_VERBS = ("get", "post", "put", "patch", "delete")

REGISTRY = {}


def _register(namespace, module):
    queues = getattr(module, "QUEUES", None)
    run = getattr(module, "run", None)
    if not (isinstance(queues, (list, tuple)) and queues and all(isinstance(queue, str) and queue for queue in queues)):
        logger.error("%s: QUEUES (1..N queue names) is required, refused", module.__name__)
        return
    if not callable(run):
        logger.error("%s: no run() function, refused", module.__name__)
        return
    declared = getattr(module, "ARGS", {})
    REGISTRY[namespace] = {"queues": list(queues), "run": run, "args": declared if isinstance(declared, dict) else {}}


for package_info in pkgutil.iter_modules(__path__):
    if not package_info.ispkg:
        continue
    if package_info.name != "_global" and package_info.name.startswith("_"):
        continue
    package = importlib.import_module(f"{__name__}.{package_info.name}")
    for module_info in pkgutil.iter_modules(package.__path__):
        if module_info.ispkg or module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{package_info.name}.{module_info.name}")
        declared_namespace = getattr(module, "NAMESPACE", None)
        if package_info.name == "_global":
            if not isinstance(declared_namespace, str) or not declared_namespace:
                logger.error("%s: NAMESPACE is missing, refused", module.__name__)
                continue
            _register(declared_namespace, module)
            continue
        if module_info.name not in ALLOWED_VERBS:
            logger.error("%s: only get/post/put/patch/delete are allowed in a metier folder, refused", module.__name__)
            continue
        expected = f"{package_info.name}:{module_info.name.upper()}"
        if declared_namespace != expected:
            logger.error("%s: NAMESPACE must be %r (found %r), refused", module.__name__, expected, declared_namespace)
            continue
        _register(expected, module)
