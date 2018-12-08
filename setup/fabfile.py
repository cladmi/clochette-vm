#! /usr/bin/env python3
"""Fabric file to setup continuous integration server for iotlab-os-ci."""

import os
import sys
import contextlib
import io

from fabric.api import env, task, runs_once, execute
from fabric.api import run, sudo, put, get
from fabric.contrib.files import append, sed
from fabric.context_managers import settings
import fabric.utils


if sys.version_info[0] != 3:
    print('Python 3 is required', file=sys.stderr)
    sys.exit(1)


CI_USER = env.user
SERVER = 'iotlab-os-ci-clochette.ci'
DISK = '/dev/vda'

HOME_CONFIG_FILE = '.profile'

# It requires having configured your .ssh/config as described in the README
env.host_string = 'root@{server}'.format(server=SERVER)
env.ssh_config_path = '~/.ssh/config'
env.use_ssh_config = True

# Add paramiko debugging
# import logging
# logging.basicConfig(level=logging.DEBUG)


@contextlib.contextmanager
def running_as_ci():
    """Context manager to connect to the server as 'ci'."""
    with settings(host_string='ci@{server}'.format(server=SERVER)):
        yield


@task
def hello_word():
    """Check we can run a command on the server."""
    run('echo Hello World ${HOSTNAME}')


@task
def setup_sudo_and_ssh_key():
    """Setup sudo no password for 'ci' and add ssh key."""
    _setup_authorized_keys()
    _setup_authorized_keys_user('ci', 'ci')

    run('apt-get update && apt-get install sudo')
    _setup_ci_sudo_nopasswd()


def _setup_ci_sudo_nopasswd(no_passwd_file='template/ci_no_passwd'):
    sudoers_tmp = '/tmp/ci_no_passwd'
    sudoers_no_passwd = '/etc/sudoers.d/ci_no_passwd'

    command = 'chown root:root {0}; mv {0} {1}'
    command = command.format(sudoers_tmp, sudoers_no_passwd)
    cmd = 'bash -c "%s"' % command  # Use bash -c command for sudo

    put(no_passwd_file, '/tmp/ci_no_passwd')
    sudo(cmd)


def _setup_authorized_keys(authorized_keys='template/authorized_keys',
                           home_dir='/root'):
    run('mkdir -p {dir}/.ssh'.format(dir=home_dir))
    put(authorized_keys, '{dir}/.ssh/authorized_keys'.format(dir=home_dir))


def _setup_authorized_keys_user(user, group):
    ci_home_dir = run('getent passwd ci | cut -d: -f6')

    _setup_authorized_keys(home_dir=ci_home_dir)
    cmd = 'chown -R {user}:{group} {dir}/.ssh'
    run(cmd.format(user=user, group=group, dir=ci_home_dir))


@task
def disable_ssh_password_auth():
    """Disable password authentication."""
    sed('/etc/ssh/sshd_config',
        r'^.*PasswordAuthentication yes', 'PasswordAuthentication no')
    run('grep PasswordAuthentication /etc/ssh/sshd_config')


@task
def create_partition():
    """Create partition with fdisk and format it."""
    partition = DISK + '1'
    mounted_cmd = 'mount -l | grep {0}'.format(DISK)
    mounted = not run(mounted_cmd, warn_only=True).return_code
    if mounted:
        return
    _fdisk(DISK)
    _mkfs_ext4(partition)


def _fdisk(disk):
    commands = r''
    commands += r'o\n'  # Create a new empty DOS partition table
    commands += r'n\n'  # Add a new partition
    commands += r'p\n'  # Primary partition
    commands += r'1\n'  # Partition number
    commands += r'\n'   # First sector (Accept default: 1)
    commands += r'\n'   # Last sector (Accept default: varies)
    commands += r'w\n'  # Write changes
    commands += r'y\n'  # Quit
    run("printf '{0}' | fdisk {1}".format(commands, disk))


def _mkfs_ext4(partition, option='-F'):
    run('mkfs.ext4 {0} {1}'.format(option, partition))


@task
def mount_builds_directory():
    """Add '/builds' directory to fstab and mount it."""
    builds_partition = DISK + '1'
    mount = '{0} /builds         ext4    defaults 0 1'.format(builds_partition)

    run('mkdir -p /builds')
    append('/etc/fstab', mount)
    run('mount -a')
    run('chown -R ci:ci /builds')


# Apt-get/aptitude recipes

@runs_once
@task
def update():
    """apt-get update"""
    sudo('apt-get update')


@task
def install(packages, options=''):
    """Install packages in non-interactive mode."""
    execute(update)
    sudo('apt-get install {0} -yqq {1}'.format(options, packages))


@task
def purge(packages, options=''):
    """Purge given package in non-interactive mode."""
    sudo('apt-get purge {0} -yqq {1}'.format(options, packages))


@task
def install_build_dep(packages, options=''):
    """Install packages build dependencies in non-interactive mode."""
    execute(update)
    sudo('apt-get build-dep -yqq {0} {1}'.format(options, packages))


@task
def upgrade():
    """Upgrade packages in non-interactive mode."""
    sudo('apt-get upgrade -yqq')
    sudo('apt-get autoremove -yqq')


@task
def dist_upgrade():
    """Dist upgrade packages in non-interactive mode."""
    sudo('apt-get dist-upgrade -yqq')
    sudo('apt-get autoremove -yqq')


@task
def apt_cache_clean():
    """Clean package cache and autoremove packages."""
    sudo('apt-get autoremove -yqq')
    sudo('apt-get clean')


@task
def setup_ci_home(ci_home='/builds/ci'):
    """Setup 'ci' user home.

    * Update ci home directory to 'ci_home'.
      By default, '/builds/ should already be mounted to an external drive
    * Save ssh key and allow jenkins access
    * Source /opt/bash_path to have custom installed packages path.
    * Re-set all files a 'ci' user as modifications where done as root
    * Get 'iotlab' user account '.iotlabrc'
    """
    _set_ci_home_path(ci_home)
    append(os.path.join(ci_home, HOME_CONFIG_FILE),
           'export PATH=${HOME}/.local/bin:${PATH}')

    _save_ssh_known_hosts()
    _setup_iotlab_account_auth_cli()

    run('chown --recursive ci:ci {0}'.format(ci_home))


def _set_ci_home_path(ci_home):
    run('usermod -m -d {0} ci'.format(ci_home))


def _save_ssh_known_hosts(known_hosts='template/known_hosts'):
    """Pre populate ci .ssh/known_hosts file for used ssh servers."""
    with running_as_ci():
        put(known_hosts, '.ssh/known_hosts')


def _setup_iotlab_account_auth_cli():
    """Setup auth-cli for iot-lab test user."""
    try:
        _check_iotlab_account_access()
    except RuntimeError:
        return
    else:
        _copy_file_from_iotlab_server('.iotlabrc')
        _copy_file_from_iotlab_server('.ssh/id_rsa', mode=0o600)


# Packages setup


@task
def install_all_packages():
    """Meta recipe that installs all packages."""
    install_common()
    install_iotlab()
    install_riot()


@task
def install_common():
    """Install common server dependencies."""
    packages = ['vim', 'tar', 'git', 'build-essential', 'aptitude']
    packages += ['python3', 'python3-dev', 'python3-pip', 'python3-virtualenv']
    packages += ['htop', 'screen', 'tmux']
    install(' '.join(packages))

    # Set bash as default environment
    run('update-alternatives --install /bin/sh sh /bin/bash 100')


@task
def install_iotlab():
    """Install iotlab specific tools."""
    packages = ['libssl-dev']
    install(' '.join(packages))

    run('pip3 install iotlabcli iotlabsshcli')


def _check_iotlab_account_access(user='iotlab', site='grenoble'):
    server = '{user}@{site}.iot-lab.info'.format(user=user, site=site)
    fabric.utils.puts('Checking connection to {server}'.format(server=server))
    with settings(host_string=server, abort_on_prompts=True,
                  abort_exception=RuntimeError):
        try:
            run('echo hello iotlab user')
        except RuntimeError:
            fabric.utils.warn(
                'Could not access {server}'.format(server=server))
            fabric.utils.warn('Ignore and keep going anyway')
            raise


def _copy_file_from_iotlab_server(file_path, user='iotlab', site='grenoble',
                                  **putkwargs):
    server = '{user}@{site}.iot-lab.info'.format(user=user, site=site)
    filebytes = io.BytesIO()
    with settings(host_string=server):
        get(file_path, filebytes)
    with running_as_ci():
        put(filebytes, file_path, **putkwargs)


@task
def install_riot():
    """Install iot-lab repository dependencies."""

    packages = ['make', 'docker.io']
    packages += ['python3-serial', 'python3-pexpect']
    packages += ['python3-cryptography', 'python3-pyasn1', 'python3-ecdsa',
                 'python3-crypto']
    install(' '.join(packages))
    disable_dns_mask_for_docker()
    run('pip3 install pytest pytest-html pyserial')


@task
def disable_dns_mask_for_docker():
    """Disable dnsmask for NetworkManager."""
    sed('/etc/NetworkManager/NetworkManager.conf',
        r'^dns=dnsmasq','#dns=dnsmasq')
    run('systemctl restart NetworkManager.service')


@task
def add_and_generate_locale():
    """Add en_US locale and generate it."""
    sed('/etc/locale.gen', '^en_US', '# en_US')
    sed('/etc/locale.gen', '# en_US.UTF-8 UTF-8', 'en_US.UTF-8 UTF-8')
    run('locale-gen')

    run('update-locale LANG=en_US.UTF-8')
    run('update-locale LC_ALL=en_US.UTF-8')
    run('update-locale LC=C')


@task
def setup():
    """Setup the whole server.

    This can be called multiple times without problems
    """
    execute(hello_word)
    execute(setup_sudo_and_ssh_key)
    execute(disable_ssh_password_auth)
    execute(create_partition)
    execute(mount_builds_directory)
    execute(setup_ci_home)
    execute(add_and_generate_locale)

    execute(update)
    execute(upgrade)
    execute(dist_upgrade)
    execute(install_all_packages)
    execute(apt_cache_clean)
