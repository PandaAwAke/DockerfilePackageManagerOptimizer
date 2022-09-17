class GlobalStatus(object):
    def __init__(self, work_dir='/', user='root'):
        self.work_dir = work_dir
        self.user = user
        self.user_dirs = {   # dir is always ends with '/'
            'root': '/root/'
        }