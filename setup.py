#!/usr/bin/env python

from distutils.core import setup

setup(
  name="pacbackup",
  description="Backup tool for the pacman installed packages",
  version="1.0.3",
  author="Adrien Bak",
  author_email="adrien.bak@gmail.com",
  scripts=['src/pacbackup.py'],
  data_files=[('share/pacbackup', ['src/pacrestore.sh']),
              ('/etc/systemd/user', ['systemd_files/pacbackup.service', 'systemd_files/pacbackup.timer'])]
  )