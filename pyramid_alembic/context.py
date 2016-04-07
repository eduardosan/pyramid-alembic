from __future__ import absolute_import
import os
import shutil
from alembic import autogenerate, util
from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext
from alembic.operations import Operations
from alembic.script.revision import ResolutionError
from alembic.script import ScriptDirectory
from sqlalchemy.engine import create_engine

try:
    from collections.abc import Iterable
except ImportError as e:
    from collections import Iterable


class Alembic(object):
    """
    Provide an Alembic environment and migration API.

    If instantiated without an app instance, :meth:`init_app` is used to register an app at a later time.

    Source: https://bitbucket.org/davidism/flask-alembic

    :param app: call :meth:`init_app` on this app
    :param run_mkdir: whether to run :meth:`mkdir` during :meth:`init_app`
    """

    def __init__(self, app_config, application_dir, metadata, run_mkdir=True):
        self.run_mkdir = run_mkdir
        self.app_config = app_config
        self.metadata = metadata
        self.application_dir = application_dir

        if run_mkdir is True:
            self.mkdir()

    @property
    def config(self):
        """
        Get the Alembic :class:`~alembic.config.Config` for the current app.
        """
        c = Config()

        script_location = self.app_config.get('script_location')
        if not os.path.isabs(script_location) and ':' not in script_location:
            script_location = os.path.join(self.application_dir, script_location)

        version_locations = [script_location]

        if self.app_config.get('version_locations') is not None:
            for item in self.app_config.get('version_locations'):
                version_location = item if isinstance(item, string_types) else item[1]

                if not os.path.isabs(version_location) and ':' not in version_location:
                    version_location = os.path.join(self.application_dir, version_location)

                version_locations.append(version_location)

        c.set_main_option('script_location', script_location)
        c.set_main_option('version_locations', ','.join(version_locations))

        return c

    @property
    def script(self):
        """
        Get the Alembic :class:`~alembic.script.ScriptDirectory` for the current app.
        """
        return ScriptDirectory.from_config(self.config)

    @property
    def env(self):
        """
        Get the Alembic :class:`~alembic.environment.EnvironmentContext` for the current app.
        """
        return EnvironmentContext(self.config, self.script)

    @property
    def context(self):
        """
        Get the Alembic :class:`~alembic.migration.MigrationContext` for the current app.
        """
        engine = create_engine(self.app_config('sqlalchemy.url'), echo=False)
        connection = engine.connect()

        env = self.env
        env.configure(
            connection=connection, target_metadata=self.metadata
        )
        return env.get_context()

    @property
    def op(self):
        """
        Get the Alembic :class:`~alembic.operations.Operations` context for the current app.
        """
        return Operations(self.context)

    def run_migrations(self, fn, **kwargs):
        """Configure an Alembic :class:`~alembic.migration.MigrationContext` to run migrations for the given function.

        This takes the place of Alembic's env.py file, specifically the ``run_migrations_online`` function.

        :param fn: use this function to control what migrations are run
        :param kwargs: extra arguments passed to revision function
        """
        engine = create_engine(self.app_config.get('sqlalchemy.url'), echo=False)
        connection = engine.connect()

        env = self.env
        env.configure(
            connection=connection, target_metadata=self.metadata, fn=fn
        )

        try:
            with env.begin_transaction():
                env.run_migrations(**kwargs)
        finally:
            connection.close()

    def mkdir(self):
        """
        Create the script directory and template.
        """
        script_dir = self.config.get_main_option('script_location')
        template_src = os.path.join(self.config.get_template_directory(), 'generic', 'script.py.mako')
        template_dest = os.path.join(script_dir, 'script.py.mako')

        if not os.access(template_src, os.F_OK):
            raise util.CommandError('Template {0} does not exist'.format(template_src))

        if not os.access(script_dir, os.F_OK):
            os.makedirs(script_dir)

        if not os.access(template_dest, os.F_OK):
            shutil.copy(template_src, template_dest)

        for version_location in self.script._version_locations:
            if not os.access(version_location, os.F_OK):
                os.makedirs(version_location)

    def current(self):
        """
        Get the list of current revisions.
        """

        return self.script.get_revisions(self.context.get_current_heads())

    def heads(self, resolve_dependencies=False):
        """Get the list of revisions that have no child revisions.

        :param resolve_dependencies: treat dependencies as down revisions
        """

        if resolve_dependencies:
            return self.script.get_revisions('heads')

        return self.script.get_revisions(self.script.get_heads())

    def branches(self):
        """Get the list of revisions that have more than one next revision."""

        return [revision for revision in self.script.walk_revisions() if revision.is_branch_point]

    def log(self, start='base', end='heads'):
        """Get the list of revisions in the order they will run.

        :param start: only get since this revision
        :param end: only get until this revision
        """
        if start is None:
            start = 'base'
        elif start == 'current':
            start = [r.revision for r in self.current()]
        else:
            start = getattr(start, 'revision', start)

        if end is None:
            end = 'heads'
        elif end == 'current':
            end = [r.revision for r in self.current()]
        else:
            end = getattr(end, 'revision', end)

        return list(self.script.walk_revisions(start, end))

    def stamp(self, target='heads'):
        """Set the current database revision without running migrations.

        :param target: revision to set to, default 'heads'
        """

        target = 'heads' if target is None else getattr(target, 'revision', target)

        def do_stamp(revision, context):
            return self.script._stamp_revs(target, revision)

        self.run_migrations(do_stamp)

    def upgrade(self, target='heads'):
        """
        Run migrations to upgrade database.

        :param target: revision to go to, default 'heads'
        """
        target = 'heads' if target is None else getattr(target, 'revision', target)
        target = str(target)

        def do_upgrade(revision, context):
            return self.script._upgrade_revs(target, revision)

        self.run_migrations(do_upgrade)

    def downgrade(self, target=-1):
        """Run migrations to downgrade database.

        :param target: revision to go down to, default -1
        """

        try:
            target = int(target)
        except ValueError:
            target = getattr(target, 'revision', target)
        else:
            if target > 0:
                target = -target

        target = str(target)

        def do_downgrade(revision, context):
            return self.script._downgrade_revs(target, revision)

        self.run_migrations(do_downgrade)

    def revision(self, message, empty=False, branch='default', parent='head', splice=False, depend=None, label=None, path=None):
        """Create a new revision.  By default, auto-generate operations by comparing models and database.

        :param message: description of revision
        :param empty: don't auto-generate operations
        :param branch: use this independent branch name
        :param parent: parent revision(s) of this revision
        :param splice: allow non-head parent revision
        :param depend: revision(s) this revision depends on
        :param label: label(s) to apply to this revision
        :param path: where to store this revision
        :return: new revision
        """

        if parent is None:
            parent = ('head',)
        elif isinstance(parent, string_types):
            parent = (parent,)
        else:
            parent = [getattr(r, 'revision', r) for r in parent]

        if label is None:
            label = []
        elif isinstance(label, string_types):
            label = [label,]
        else:
            label = list(label)

        # manage independent branches
        if branch:
            for i, item in enumerate(parent):
                if item in ('base', 'head'):
                    parent[i] = '{}@{}'.format(branch, item)

            if not path:
                branch_path = dict(item for item in current_app.config['ALEMBIC']['version_locations'] if not isinstance(item, string_types)).get(branch)

                if branch_path:
                    path = branch_path

            try:
                branch_exists = any(r for r in self.script.revision_map.get_revisions(branch) if r is not None)
            except ResolutionError:
                branch_exists = False

            if not branch_exists:
                # label the first revision of a separate branch and start it from base
                label.insert(0, branch)
                parent = ('base',)

        if not path:
            path = self.script.dir

        # relative path is relative to app root
        if path and not os.path.isabs(path) and ':' not in path:
            path = os.path.join(current_app.root_path, path)

        template_args = {
            'config': self.config
        }

        if empty:
            def do_revision(revision, context):
                return []
        else:
            def do_revision(revision, context):
                if set(self.script.get_revisions(revision)) != set(self.script.get_revisions('heads')):
                    raise util.CommandError('Target database is not up to date')

                autogenerate._produce_migration_diffs(context, template_args, set())
                return []

        if not empty or util.asbool(self.config.get_main_option('revision_environment')):
            self.run_migrations(do_revision)

        return self.script.generate_revision(
            util.rev_id(), message,
            head=parent, splice=splice, depends_on=depend,
            branch_labels=label, version_path=path,
            **template_args
        )

    def merge(self, revisions='heads', message=None, label=None):
        """Create a merge revision.

        :param revisions: revisions to merge
        :param message: description of merge, will default to revisions param
        :param label: label(s) to apply to this revision
        :return: new revision
        """

        if not revisions:
            revisions = ('heads',)
        elif isinstance(revisions, string_types):
            revisions = (revisions,)
        else:
            revisions = [getattr(r, 'revision', r) for r in revisions]

        if message is None:
            message = 'merge {0}'.format(', '.join(revisions))

        if isinstance(label, string_types):
            label = (label,)

        return self.script.generate_revision(
            util.rev_id(), message,
            head=revisions,
            branch_labels=label,
            config=self.config
        )

    def compare_metadata(self):
        """
        Generate a list of operations that would be present in a new revision.
        """

        return autogenerate.compare_metadata(self.context, self.metadata)
