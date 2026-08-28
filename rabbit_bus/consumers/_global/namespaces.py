NAMESPACE = "namespaces"


def run(args):
    # Imported lazily: this module is loaded while the consumers package is
    # still building its own registry.
    import consumers
    import publishers

    return {
        "consumers": {name: consumers.ARGS.get(name, {}) for name in sorted(consumers.REGISTRY)},
        # A mirror publisher shares its consumer's namespace: sending that
        # namespace runs the consumer, so only free-standing publishers are
        # callable entry points and listed here.
        "publishers": {name: publishers.REGISTRY[name]["args"] for name in sorted(publishers.REGISTRY) if name not in consumers.REGISTRY},
    }
