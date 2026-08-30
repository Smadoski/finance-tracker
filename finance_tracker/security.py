def auth_enabled(get_setting):
    return get_setting("auth_required", "0") == "1"

def tailnet_only_enabled(get_setting):
    return get_setting("tailnet_only", "1") == "1"
