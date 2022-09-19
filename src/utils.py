
def substitute_env(s: str, context) -> str:
    need_to_substitute_keys = []
    for key, _ in context.envs.items():
        if (s.find('${' + key + '}') != -1 or s.find('$' + key) != -1) and \
                key not in need_to_substitute_keys:
            need_to_substitute_keys.append(key)
    for key in need_to_substitute_keys:
        value = context.envs[key]
        s = s.replace('${' + key + '}', value)
        s = s.replace('$' + key, value)
    return s
