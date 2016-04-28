from __future__ import absolute_import
import subprocess
import sys
import os.path


class Alembic(object):
    """
    Provide an Alembic environment and migration API.

    If instantiated without an app instance, :meth:`init_app` is used to register an app at a later time.

    Source: https://bitbucket.org/davidism/flask-alembic

    :param app: call :meth:`init_app` on this app
    :param run_mkdir: whether to run :meth:`mkdir` during :meth:`init_app`
    """

    def __init__(self, config_file, application_dir, environment=None):
        self.config_file = config_file
        self.application_dir = application_dir
        self.environment = environment

    def upgrade(self):
        """
        Run alembic upgrade
        """
        p = subprocess.Popen([
            os.path.dirname(sys.executable) + "/alembic",
            '-c', self.config_file,
            'upgrade',
            'head'
        ],
            cwd=self.application_dir,
            close_fds=True,
            env=self.environment
        )
