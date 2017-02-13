from __future__ import print_function, unicode_literals

from StringIO import StringIO
import os
import re
import sys
from contextlib import contextmanager
from functools import wraps
from importlib import import_module
from getpass import getpass
from posixpath import join

from fabric.api import abort, env, cd, prefix, sudo as _sudo, run as _run, \
    hide, task, local as lrun
from fabric.context_managers import settings as fab_settings
from fabric.contrib.console import confirm
from fabric.contrib.files import exists, upload_template
from fabric.contrib.project import rsync_project
from fabric.colors import yellow, green, blue, red
from fabric.decorators import hosts

from master import settings

################
# Config setup #
################

env.proj_name = settings.COREAPP
env.app_name = settings.COREAPP

conf = {}
if sys.argv[0].split(os.sep)[-1] in ("fab", "fab-script.py"):
    # Ensure we import settings from the current dir
    try:
        conf = import_module('master.settings').FABRIC
        try:
            conf["HOSTS"][0]
        except (KeyError, ValueError):
            raise ImportError
    except (ImportError, AttributeError):
        print("Aborting, no hosts defined.")
        exit()

env.user = conf.get("SSH_USER")
env.password = conf.get("SSH_PASS", None)
env.key_filename = conf.get("SSH_KEY_PATH")
env.hosts = conf.get("HOSTS")
env.compress_offline = conf.get("COMPRESS_OFFLINE", False)
env.venv_home = conf.get("VIRTUALENV_HOME", "/home/%s/.virtualenv" % env.user)
env.venv_path = join(env.venv_home, env.proj_name)
env.proj_path = "/home/%s/%s" % (env.user, env.proj_name)
env.log_path = "/home/%s/logs" % env.user
env.home_user = "/home/%s" % env.user

env.manage = "source %s/bin/activate; cd %s; python manage.py" % (env.venv_path, env.proj_path)

env.domains = conf.get("DOMAINS")

env.domains_nginx = " ".join(env.domains)
env.domains_regex = "|".join(env.domains)
env.domains_python = ", ".join(["'%s'" % s for s in env.domains])
env.vcs_tools = ["git"]
env.deploy_tool = conf.get("DEPLOY_TOOL")  # git or rsync accepted
env.repo_url = conf.get("REPOSITORY_REMOTE_URL")
env.reqs_path = conf.get("REQUIREMENTS_PATH", "requirements.txt")
env.locale = conf.get("LOCALE", "en_US.UTF-8")
env.num_workers = "multiprocessing.cpu_count() * 2 + 1"

env.secret_key = conf.get("SECRET_KEY")
env.nevercache_key = conf.get("NEVERCACHE_KEY")
env.staticfiles_path = conf.get("STATICFILES_PATH")
env.media_path = conf.get("MEDIA_PATH")

# Remote git repos need to be "bare" and reside separated from the project
if env.deploy_tool == "git":
    env.repo_path = env.proj_path  # We use same config
else:
    env.repo_path = env.proj_path


##################
# Template setup #
##################

# Each template gets uploaded at deploy time, only if their
# contents has changed, in which case, the reload command is
# also run.

templates = {
    "nginx": {
        "local_path": "deploy/nginx.conf.template",
        "remote_path": "/etc/nginx/sites-enabled/%(proj_name)s.conf",
        "reload_command": "sudo /etc/init.d/nginx restart",
    },
    "supervisor": {
        "local_path": "deploy/supervisor.conf.template",
        "remote_path": "/etc/supervisor/conf.d/%(proj_name)s.conf",
        "reload_command": "sudo supervisorctl update gunicorn_%(proj_name)s",
    },
    "gunicorn": {
        "local_path": "deploy/gunicorn.conf.py.template",
        "remote_path": "%(proj_path)s/master/gunicorn.conf.py",
    },
    "celery": {
        "local_path": "deploy/celery.template",
        "remote_path": "/etc/supervisor/conf.d/celery_%(proj_name)s.conf",
        "reload_command": "sudo supervisorctl update celery_%(proj_name)s",
    },
    "celerybeat": {
        "local_path": "deploy/celerybeat.template",
        "remote_path": "/etc/supervisor/conf.d/celerybeat_%(proj_name)s.conf",
        "reload_command": "sudo supervisorctl update celerybeat_%(proj_name)s",
    },
    "updatemedia": {
        "local_path": "deploy/update_media_worker.template",
        "remote_path": "/etc/supervisor/conf.d/update_media_worker.conf",
        "reload_command": "sudo supervisorctl update update_media_%(proj_name)s",
    },
}


######################################
# Context for virtualenv and project #
######################################

@contextmanager
def virtualenv():
    """
    Runs commands within the project's virtualenv.
    """
    with cd(env.venv_path):
        with prefix("source %s/bin/activate" % env.venv_path):
            yield


@contextmanager
def project():
    """
    Runs commands within the project's directory.
    """
    with virtualenv():
        with cd(env.proj_path):
            yield


@contextmanager
def update_changed_requirements():
    """
    Checks for changes in the requirements file across an update,
    and gets new requirements if changes have occurred.
    """
    #reqs_path = join(env.proj_path, env.reqs_path)
    reqs_path = "%s/%s" % (env.proj_path, env.reqs_path)
    get_reqs = lambda: run("cat %s" % reqs_path, show=False)
    old_reqs = get_reqs() if env.reqs_path else ""
    yield
    if old_reqs:
        new_reqs = get_reqs()
        if old_reqs == new_reqs:
            # Unpinned requirements should always be checked.
            for req in new_reqs.split("\n"):
                if req.startswith("-e"):
                    if "@" not in req:
                        # Editable requirement without pinned commit.
                        break
                elif req.strip() and not req.startswith("#"):
                    if not set(">=<") & set(req):
                        # PyPI requirement without version.
                        break
            else:
                # All requirements are pinned.
                return
        pip("-r %s/%s" % (env.proj_path, env.reqs_path))


###########################################
# Utils and wrappers for various commands #
###########################################

def _print(output):
    print()
    print(output)
    print()


def print_command(command):
    _print(blue("$ ", bold=True) +
           yellow(command, bold=True) +
           red(" ->", bold=True))


@task
def run(command, show=True, *args, **kwargs):
    """
    Runs a shell comand on the remote server.
    """
    if show:
        print_command(command)
    with hide("running"):
        return _run(command, *args, **kwargs)


@task
def sudo(command, show=True, *args, **kwargs):
    """
    Runs a command as sudo on the remote server.
    """
    if show:
        print_command(command)
    with hide("running"):
        return _sudo(command, *args, **kwargs)


def log_call(func):
    @wraps(func)
    def logged(*args, **kawrgs):
        header = "-" * len(func.__name__)
        _print(green("\n".join([header, func.__name__, header]), bold=True))
        return func(*args, **kawrgs)
    return logged


def get_templates():
    """
    Returns each of the templates with env vars injected.
    """
    injected = {}
    for name, data in templates.items():
        injected[name] = dict([(k, v % env) for k, v in data.items()])
    return injected


def upload_template_and_reload(name):
    """
    Uploads a template only if it has changed, and if so, reload the
    related service.
    """
    template = get_templates()[name]
    local_path = template["local_path"]
    if not os.path.exists(local_path):
        project_root = os.path.dirname(os.path.abspath(__file__))
        local_path = os.path.join(project_root, local_path)
    remote_path = template["remote_path"]
    reload_command = template.get("reload_command")
    owner = template.get("owner")
    mode = template.get("mode")
    remote_data = ""
    if exists(remote_path):
        with hide("stdout"):
            remote_data = run("cat %s" % remote_path, show=False)

    with open(local_path, "r") as f:
        local_data = f.read()
        # Escape all non-string-formatting-placeholder occurrences of '%':
        local_data = re.sub(r"%(?!\(\w+\)s)", "%%", local_data)
        if "%(db_pass)s" in local_data:
            env.db_pass = db_pass()
        local_data %= env

    clean = lambda s: s.replace("\n", "").replace("\r", "").strip()

    if clean(remote_data) == clean(local_data):
        print("Template %s, nothing to do..." % name)
        return
    else:
        print("Updating template %s" % name)

    local_data = local_data.encode('utf-8')

    try:
        upload_template(local_path, remote_path, env, use_sudo=False)
    except TypeError:
        upload_template(local_path, remote_path, use_sudo=False)

    if owner:
        sudo("chown %s %s" % (owner, remote_path))
    if mode:
        sudo("chmod %s %s" % (mode, remote_path))
    if reload_command:
        run(reload_command)


def rsync_upload():
    """
    Uploads the project with rsync excluding some files and folders.
    """
    excludes = ["*.pyc", "*.pyo", "*.sqlite", ".DS_Store", ".coverage", "instanalysis/media",
                "websiteconfig.py", "/.git", "/.hg", "local_settings.py"]
    local_dir = os.getcwd() + os.sep
    return rsync_project(remote_dir=env.proj_path, local_dir=local_dir,
                         exclude=excludes)

def vcs_create():
    """ Creates a fresh repository in remote
    """
    if env.deploy_tool == "git":
        # Requesting user for the tag to checkout
        with cd(env.home_user):
            run("rm -rf %s/yoinable" % env.home_user)
            run("git clone %s" % env.repo_url)  # Retrieving
    else:
        print("Mercurial Not supported yet")
        exit(0)

def get_remote_commit(repo_path):
    fh = StringIO();
    with cd(repo_path):
        out = run("git rev-parse HEAD", stdout=fh)
        return out

def vcs_upload(name_branch="stable"):
    """
    Updates the project with the selected VCS tool.
    """
    local_commit = lrun("git rev-parse HEAD", capture=True).lstrip()
    remote_commit = get_remote_commit(env.repo_path)

    # Requesting user for the tag to checkout
    with cd(env.repo_path):
        if(local_commit == remote_commit):
            print(yellow("HEAD in same commit in both local and remote. Not updating repository"))
            return
        else:
            cmd = 'eval "$(ssh-agent -s)"; ssh-add ~/.ssh/github; git pull origin %s; git checkout %s' % (name_branch, name_branch)
            run(cmd)  # Retrieving


def db_pass():
    """
    Prompts for the database password if unknown.
    """
    if not env.db_pass:
        env.db_pass = getpass("Enter the database password: ")
    return env.db_pass


@task
def apt(packages):
    """
    Installs one or more system packages via apt.
    """
    return sudo("apt-get install -y -q " + packages)


@task
def pip(packages):
    """
    Installs one or more Python packages within the virtual environment.
    """
    with virtualenv():
        return run("pip install %s" % packages)


def postgres(command):
    """
    Runs the given command as the postgres user.
    """
    show = not command.startswith("psql")
    return sudo(command, show=show, user="postgres")


@task
def psql(sql, show=True):
    """
    Runs SQL against the project's database.
    """
    out = postgres('psql -c "%s"' % sql)
    if show:
        print_command(sql)
    return out


@task
def backup(filename):
    """
    Backs up the project database.
    """
    tmp_file = "/tmp/%s" % filename
    # We dump to /tmp because user "postgres" can't write to other user folders
    # We cd to / because user "postgres" might not have read permissions
    # elsewhere.
    with cd("/"):
        postgres("pg_dump -Fc %s > %s" % (env.db_name, tmp_file))
    run("cp %s ." % tmp_file)
    sudo("rm -f %s" % tmp_file)


@task
def restore(filename):
    """
    Restores the project database from a previous backup.
    """
    return postgres("pg_restore -c -d %s %s" % (env.proj_name, filename))


@task
def python(code, show=True):
    """
    Runs Python code in the project's virtual environment, with Django loaded.
    """
    setup = "import os;" \
            "os.environ[\'DJANGO_SETTINGS_MODULE\']=\'master.settings\';" \
            "import django;" \
            "django.setup();"
    full_code = 'python -c "%s%s"' % (setup, code.replace("`", "\\\`"))
    with project():
        if show:
            print_command(code)
        result = run(full_code, show=False)
    return result


def static():
    """
    Returns the live STATIC_ROOT directory.
    """
    return python("from django.conf import settings;"
                  "print(settings.STATIC_ROOT)", show=False).split("\n")[-1]


@task
def manage(command):
    """
    Runs a Django management command.
    """
    print("%s %s" % (env.manage, command))
    return run("%s %s" % (env.manage, command))


###########################
# Security best practices #
###########################

@task
@log_call
@hosts(["root@%s" % host for host in env.hosts])
def secure(new_user=env.user):
    """
    Minimal security steps for brand new servers.
    Installs system updates, creates new user (with sudo privileges) for future
    usage, and disables root login via SSH.
    """
    run("apt-get update -q")
    run("apt-get upgrade -y -q")
    run("adduser --gecos '' %s" % new_user)
    run("usermod -G sudo %s" % new_user)
    run("sed -i 's:RootLogin yes:RootLogin no:' /etc/ssh/sshd_config")
    run("service ssh restart")
    print(green("Security steps completed. Log in to the server as '%s' from "
                "now on." % new_user, bold=True))


#########################
# Install and configure #
#########################

@task
@log_call
def install():
    """
    Installs the base system and Python requirements for the entire server.
    """
    # Install system requirements
    #sudo("apt-get update -y -q")
    #apt("nginx libjpeg-dev python-dev python-setuptools git-core libgeos-dev postgis* "
    #    "libpq-dev memcached supervisor python-pip libxml2-dev libxslt1-dev redis-server")

    # Install Python requirements
    #sudo("pip install -U pip virtualenv virtualenvwrapper")

    # Set up virtualenv
    run("mkdir -p %s" % env.venv_home)
    run("echo 'export WORKON_HOME=%s' >> /home/%s/.bashrc" % (env.venv_home,
                                                              env.user))
    run("echo 'source /usr/local/bin/virtualenvwrapper.sh' >> "
        "/home/%s/.bashrc" % env.user)
    print(green("Successfully set up git, pip, virtualenv, "
                "supervisor, memcached.", bold=True))


@task
@log_call
def update_py_reqs():
    with project():
        if env.reqs_path:
            pip("-r %s/%s" % (env.proj_path, env.reqs_path))

        pip("gunicorn setproctitle python-memcached")



@task
@log_call
def create():
    """
    Creates the environment needed to host the project.
    The environment consists of: system locales, virtualenv, database, project
    files, SSL certificate, and project-specific Python requirements.
    """
    # Generate project locale
    locale = env.locale.replace("UTF-8", "utf8")
    with hide("stdout"):
        if locale not in run("locale -a"):
            sudo("locale-gen %s" % env.locale)
            sudo("update-locale %s" % env.locale)
            run("exit")

    # Create project path if not vcs
    if env.deploy_tool not in env.vcs_tools:
        run("mkdir -p %s" % env.proj_path)

    # Set up virtual env
    run("mkdir -p %s" % env.venv_home)
    with cd(env.venv_home):
        if exists(env.proj_name):
            if confirm("Project already exists in host server: %s"
                       "\nWould you like to replace it?" % env.proj_name):
                run("rm -rf %s" % env.proj_name)
                run("virtualenv %s" % env.proj_name)

    # Upload project files
    if env.deploy_tool in env.vcs_tools:
        vcs_create()
    else:
        rsync_upload()

    with cd(env.proj_path):
        run("mkdir -p master/logs/")

    # Dropping table if already exists.
    # user_sql = "DROP DATABASE IF EXISTS %s;" % env.db_name
    # psql(user_sql, show=False)

    # # Dropping user if it already exists.
    # user_sql = "DROP USER IF EXISTS %s;" % env.db_user
    # psql(user_sql, show=False)

    # Create DB and DB user
    # pw = db_pass()
    # pw_db = pw.replace("'", "\'")
    # user_sql_args = (env.db_user, pw_db)

    # user_sql = "CREATE USER %s WITH ENCRYPTED PASSWORD '%s';" % user_sql_args
    # psql(user_sql, show=False)
    # shadowed = "*" * len(pw)
    # print_command(user_sql.replace("'%s'" % pw, "'%s'" % shadowed))
    # psql("CREATE DATABASE %s WITH OWNER %s ENCODING = 'UTF8' "
    #      "LC_CTYPE = '%s' LC_COLLATE = '%s' TEMPLATE template0;" %
    #      (env.db_name, env.db_user, env.locale, env.locale))

    #creating database sqlite3 This is needed for sqlite only!!!


    # Set up SSL certificate

    update_py_reqs()

    with cd(env.proj_path):
        manage("makemigrations instanalysis")
        manage("migrate")


    return True

@task
@log_call
def remove():
    """
    Blow away the current project.
    """
    if exists(env.venv_path):
        run("rm -rf %s" % env.venv_path)
    if exists(env.proj_path):
        run("rm -rf %s" % env.proj_path)
    for template in get_templates().values():
        remote_path = template["remote_path"]
        if exists(remote_path):
            sudo("rm %s" % remote_path)
    if exists(env.repo_path):
        run("rm -rf %s" % env.repo_path)
    sudo("supervisorctl update")
    psql("DROP DATABASE IF EXISTS %s;" % env.proj_name)
    psql("DROP USER IF EXISTS %s;" % env.proj_name)


##############
# Deployment #
##############

@task
@log_call
def restart(process_name=None):
    """
    Restart gunicorn worker processes for the project.
    If the processes are not running, they will be started.
    """
    if process_name is not None:
        run("sudo supervisorctl restart %s" % process_name)
    else:
        pid_path = "%s/gunicorn.pid" % env.proj_path
        if exists(pid_path):
            with fab_settings(warn_only=True):
                run("kill -HUP `cat %s`" % pid_path)
        else:
            run("sudo supervisorctl update")
            run("sudo supervisorctl restart gunicorn_%s" % env.proj_name)
            run("sudo supervisorctl restart celery_%s" % env.proj_name)
            run("sudo supervisorctl restart celerybeat_%s" % env.proj_name)
            run("sudo supervisorctl restart update_media_%s" % env.proj_name)
            print(green("Restart completed!"))


@task
@log_call
def deploy(branch="stable"):
    """
    Deploy latest version of the project.
    Backup current version of the project, push latest version of the project
    via version control or rsync, install new requirements, sync and migrate
    the database, collect any new static assets, and restart gunicorn's worker
    processes for the project.
    """
    if not exists(env.proj_path):
        if confirm("Project does not exist in host server: %s"
                   "\nWould you like to create it?" % env.proj_name):
            create()
        else:
            abort()

    with cd(join(env.proj_path, "..")):
        # Making backup
        excludes = ["*.pyc", "*.pio", "*.thumbnails"]
        exclude_arg = " ".join("--exclude='%s'" % e for e in excludes)
        #run("tar -cf {0}.tar {1} {2}".format(env.proj_name, exclude_arg, env.proj_name))

        # Deploy latest version of the project
        with update_changed_requirements():
            if env.deploy_tool in env.vcs_tools:
                vcs_upload(branch)
            else:
                rsync_upload()

    for name in get_templates():
        upload_template_and_reload(name)

    with cd(env.proj_path):
        manage("migrate")
        if env.compress_offline:
            manage("compress")

    with cd(env.proj_path):
        manage("collectstatic --no-input")

    restart()
    return True


@task
@log_call
def rollback():
    """
    Reverts project state to the last deploy.
    When a deploy is performed, the current state of the project is
    backed up. This includes the project files, the database, and all static
    files. Calling rollback will revert all of these to their state prior to
    the last deploy.
    """
    with update_changed_requirements():
        if env.deploy_tool in env.vcs_tools:
            with cd(env.repo_path):
                if env.deploy_tool == "git":
                        run("GIT_WORK_TREE={0} git checkout -f "
                            "`cat {0}/last.commit`".format(env.proj_path))
                elif env.deploy_tool == "hg":
                        run("hg update -C `cat last.commit`")
            with project():
                with cd(join(static(), "..")):
                    run("tar -xf %s/static.tar" % env.proj_path)
        else:
            with cd(env.proj_path.rsplit("/", 1)[0]):
                run("rm -rf %s" % env.proj_name)
                run("tar -xf %s.tar" % env.proj_name)
    with cd(env.proj_path):
        restore("last.db")
    restart()


@task
@log_call
def all():
    """
    Installs everything required on a new system and deploy.
    From the base software, up to the deployed project.
    """
    install()
    if create():
        deploy()
