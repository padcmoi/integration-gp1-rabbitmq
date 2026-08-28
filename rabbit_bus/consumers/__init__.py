"""Consumers, organised by business folder.

consumers/_global/      global namespaces, one file each, NAMESPACE declared
consumers/<domaine>/     one folder per business domain, named after the GP1 route it
                        mirrors (/honoraires_edl -> honoraires_edl/); ONLY the
                        five verbs get.py post.py put.py patch.py delete.py are
                        allowed, and each file declares its NAMESPACE, checked
                        against the path: honoraires_edl/get.py must declare
                        "honoraires_edl:GET"

Folders starting with "_" other than _global are reserved for the bus, and so
are files starting with "_" (_django.py). A file that breaks a rule is refused
with an error in the journal and never registered.

An optional ARGS dict ({name: example value}) declares the expected arguments.
"""

import importlib
import logging
import pkgutil

logger = logging.getLogger("bus.registry")

ALLOWED_VERBS = ("get", "post", "put", "patch", "delete")

REGISTRY = {}
ARGS = {}


def _register(namespace, module):
    run = getattr(module, "run", None)
    if not callable(run):
        logger.error("%s: no run(args) function, refused", module.__name__)
        return
    REGISTRY[namespace] = run
    declared = getattr(module, "ARGS", {})
    ARGS[namespace] = declared if isinstance(declared, dict) else {}


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
            logger.error("%s: only get/post/put/patch/delete are allowed in a business folder, refused", module.__name__)
            continue
        expected = f"{package_info.name}:{module_info.name.upper()}"
        if declared_namespace != expected:
            logger.error("%s: NAMESPACE must be %r (found %r), refused", module.__name__, expected, declared_namespace)
            continue
        _register(expected, module)
