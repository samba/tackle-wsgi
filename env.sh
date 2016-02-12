#!/bin/sh

[ -f $0 ] && exit 1

which pip || sudo easy_install pip
which virtualenv || sudo pip install virtualenv

[ -d virtenv ] || virtualenv ./virtenv
. ./virtenv/bin/activate

pip install --upgrade -r requirements_dev.txt