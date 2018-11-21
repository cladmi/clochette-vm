CI for RIOT testing with IoT-LAB
================================

It requires having

    python3
    fabric3


Accessing the server
--------------------

Add the following to your `~/.ssh/config`:

Host iotlab-os-ci-clochette.ci
    Hostname iotlab-os-ci-clochette
    User root
    ProxyCommand ssh REPLACE_WITH_YOUR_INRIA_CI_SSH_LOGIN@ci-ssh.inria.fr -W %h:%p


Accessing the iotlab account
----------------------------

You should also have normally access to the 'iotlab' test account with your ssh
key. If you do not have, it is ignored and this setup is not done.


Installing
==========

Run only

    fab setup

It takes care of everything and is idempotent
