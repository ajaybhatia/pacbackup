#!/usr/bin/python

import argparse

import pyalpm
from pycman import config

import os, shutil
import datetime

import pygit2

__version__ = '1.0.3'

"""
This module is a part of PacBackup. It backs up the package list along with a scipt 
allowing easy recovery.
"""


def sanitize_path(path):
  return os.path.abspath(os.path.expanduser(path))

def pkg_info_str(pkg):
  return str(pkg.name)

class PacBackup:
  def __init__(self, options):
    self.handle = config.init_with_config_and_options(options)
    self.backup_file_path = sanitize_path(options.backup_config)
    self.container = os.path.abspath(os.path.join(self.backup_file_path, os.pardir))
    self.verbosity = options.verbose

  def retrieve_pkg_lists(self):
    available_pkgs = {}
    for db in self.handle.get_syncdbs():
      for pkg in db.pkgcache:
        available_pkgs[pkg.name] = db.name

    db = self.handle.get_localdb()

    self.pkg_lists = {}

    for pkg in db.pkgcache:
      if pkg.reason == pyalpm.PKG_REASON_EXPLICIT:
        try :
          if available_pkgs[pkg.name] not in self.pkg_lists:
            self.pkg_lists[available_pkgs[pkg.name]] = []
          self.pkg_lists[available_pkgs[pkg.name]].append(pkg)
        except KeyError:
          if "AUR" not in self.pkg_lists:
            self.pkg_lists["AUR"] = []
          self.pkg_lists["AUR"].append(pkg)

    if self.verbosity :
      for k in self.pkg_lists:
        print(k)
        for v in self.pkg_lists[k]:
          print("\t" + pkg_info_str(v))

  def prepare_backup_folder(self):
    print("Preparing backup folder : ", self.container)
    os.mkdir(self.container)
    pygit2.init_repository(self.container, False)

    # look for the restore script in the default install dir first
    try:
      shutil.copy2("/usr/share/pacbackup/pacrestore.sh", self.container)
    except FileNotFoundError:
      try:
        shutil.copy2(os.path.join(os.path.dirname(os.path.realpath(__file__)),
          "pacrestore.sh"), self.container)
      except FileNotFoundError:
        print("Couldn't find the restore script anywhere, try reinstalling", file=stderr)
        shutil.rmtree(self.container)
        exit()

    repo = pygit2.Repository(self.container)
    index = repo.index

    index.read()
    index.add_all()
    index.write()
    tree = index.write_tree()

    message = "Initial Commit - Automated Package List Backup"
    comitter = pygit2.Signature('PacBackup '+__version__, '')
    sha = repo.create_commit('HEAD', 
      comitter, comitter, message, 
      tree, 
      [])


  def backup_pkg_lists(self):
    if not os.path.exists(self.container):
      self.prepare_backup_folder()

    with open(self.backup_file_path, 'w+') as backup:
      backup.write("# Generated by PacBackup "+__version__+"\n")
      for db in self.handle.get_syncdbs():
        backup.write("["+db.name+"]\n")
        for pkg in self.pkg_lists[db.name]:
          backup.write(pkg_info_str(pkg) + "\n")
        backup.write("\n")
        self.pkg_lists.pop(db.name, None)
      for k in self.pkg_lists:
        backup.write("["+k+"]\n")
        for pkg in self.pkg_lists[k]:
          backup.write(pkg_info_str(pkg) + "\n")
        backup.write("\n")

  def add_to_git(self):
    local_path = os.path.relpath(self.backup_file_path, self.container)
    repo = pygit2.Repository(self.container)
    st = repo.status()

    if st:
      index = repo.index
      index.read()
      index.add(local_path)

      index.write()
      tree = index.write_tree()

      today = datetime.date.today().strftime("%B %d, %Y")
      message = today + " - Automated Package List Backup"
      comitter = pygit2.Signature('PacBackup '+__version__, 'pacbackup@dummy.org')

      parents = [repo.head.get_object().hex]

      sha = repo.create_commit('refs/heads/master',
       comitter, comitter, message, 
       tree,
       parents)
    else:
      print("No local changes to commit")


def main():
  parser = config.make_parser(description='Backs-up the list of pacman-installed packages on the system.', 
    prog = 'pacbackup')

  group = parser.add_argument_group("Backup options")
  group.add_argument('--backup-config', metavar='<path>', default='~/.pacbackup/pkglist', 
    help = "specifies the backup file location, default : ~/.pacbackup/pkglist")

  backup = PacBackup(parser.parse_args())
  print("Retriving current package list")
  backup.retrieve_pkg_lists()
  print("Backing package list up")
  backup.backup_pkg_lists()
  print("Committing the backup to the local git tree")
  backup.add_to_git()


if __name__ == '__main__':
  main()
