#! /usr/bin/env python

import optparse as op
import os
import subprocess as sp
import time

__usage__ = "%prog [OPTIONS] DIRECTORY"

def is_repo(d):
    if not os.path.isdir(d):
        return False
    if not os.path.isdir(os.path.join(d, 'objects')):
        return False
    if not os.path.isdir(os.path.join(d, 'refs')):
        return False

    headref = os.path.join(d, 'HEAD')
    if os.path.isfile(headref):
        return True
    if os.path.islinke(headref) and os.readlink(headref).startswith("refs"):
        return True
    return False

def find_repo(path):
    if is_repo(path):
        return True
    if is_repo(os.path.join(path, '.git')):
        return True
    (parent, ignore) = os.path.split(path)
    if parent == path:
        return False
    return find_repo(parent)

def get_config(key):
    p = sp.Popen(['git', 'config', key], stdin=sp.PIPE, stdout=sp.PIPE)
    (value, stderr) = p.communicate()
    return value.strip()

def make_when(timestamp=None):
    if timestamp is None:
        timestamp = int(time.time())
    currtz = "%+05d" % (time.timezone / 36) # / 3600 * 100
    return "%s %s" % (timestamp, currtz)

def start_commit(pipe, message):
    username = get_config("user.name")
    email = get_config("user.email")
    pipe.stdin.write('commit refs/heads/gh-pages\n')
    pipe.stdin.write('committer %s <%s> %s\n' % (username, email, make_when()))
    pipe.stdin.write('data %d\n%s\n' % (len(message), message))
    pipe.stdin.write('deleteall\n')

def add_file(pipe, srcpath, tgtpath):
    pipe.stdin.write('M 100644 inline %s\n' % tgtpath)
    with open(srcpath) as handle:
        data = handle.read()
        pipe.stdin.write('data %d\n' % len(data))
        pipe.stdin.write(data)
        pipe.stdin.write('\n')

def run_import(srcdir, message):
    pipe = sp.Popen(['git', 'fast-import', '--date-format=raw'], stdin=sp.PIPE)
    start_commit(pipe, message)
    for path, dnames, fnames in os.walk(srcdir):
        for fn in fnames:
            fpath = os.path.join(path, fn)
            add_file(pipe, fpath, os.path.relpath(fpath, start=srcdir))
    pipe.stdin.write('\n')
    pipe.stdin.close()
    if pipe.wait() != 0:
        print "Failed to process commit."

def options():
    return [
        op.make_option('-m', dest='mesg', default='Update documentation',
            help='The commit message to use on the gh-pages branch.'),
        op.make_option('-p', dest='push', default=False, action='store_true',
            help='Push the branch to origin/gh-pages after committing.'),
        op.make_option('-r', dest='remote', default='origin',
            help='The name of the remote to push to. [%default]')
    ]

def main():
    parser = op.OptionParser(usage=__usage__, option_list=options())
    opts, args = parser.parse_args()

    if len(args) == 0:
        parser.error("No import directory specified.")

    if len(args) > 1:
        parser.error("Unknown arguments specified: %s" % ', '.join(args[1:]))

    if not os.path.isdir(args[0]):
        parser.error("Not a directory: %s" % args[0])

    if not find_repo(os.getcwd()):
        parser.error("No Git repository found.")

    run_import(args[0], opts.mesg)

if __name__ == '__main__':
    main()

