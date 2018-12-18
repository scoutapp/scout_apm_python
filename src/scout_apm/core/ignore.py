from scout_apm.core.context import AgentContext


def ignore_path(path):
    ignored_paths = AgentContext.instance.config.value("ignore")
    for ignored in ignored_paths:
        if path.startswith(ignored):
            return True
    return False
