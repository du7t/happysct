import os


def get_sysfs_stat(path=''):
    assert path
    if os.path.exists(path):
        with open(path) as f:
            lines = f.readlines()
    else:
        lines = None
    return lines


def get_max_memory_usage():
    tmp = get_sysfs_stat('/sys/fs/cgroup/memory/memory.max_usage_in_bytes')
    if tmp:
        memory_max_usage = int(tmp[0].strip())
    else:
        memory_max_usage = 0
    return memory_max_usage


def get_memory_usage():
    tmp = get_sysfs_stat('/sys/fs/cgroup/memory/memory.usage_in_bytes')
    if tmp:
        memory_usage = int(tmp[0].strip())
    else:
        memory_usage = 0
    return memory_usage


def get_memory_limit():
    tmp = get_sysfs_stat('/sys/fs/cgroup/memory/memory.stat')
    if not tmp:
        memory_limit = 0
    else:
        for item in tmp:
            if 'hierarchical_memory_limit' in item:
                memory_limit = int(item.split(' ')[1].strip())
                break
    return memory_limit
