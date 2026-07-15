class WorkspaceSettings:
    def __init__(self):
        self.theme = "dark"
        self.locale = "en"
        self.items_per_page = 25
        self.report_label = "passforge-healthy"


def deep_merge(src: dict, dst) -> None:
    for key, value in src.items():
        if hasattr(dst, "__getitem__"):
            if dst.get(key) is not None and isinstance(value, dict):
                deep_merge(value, dst.get(key))
            else:
                dst[key] = value
        elif hasattr(dst, key) and isinstance(value, dict):
            deep_merge(value, getattr(dst, key))
        else:
            setattr(dst, key, value)
