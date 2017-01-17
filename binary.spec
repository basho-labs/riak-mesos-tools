# -*- mode: python -*-


import os
import glob


def extra_datas(mydir):
    def rec_glob(p, files):
        for d in glob.glob(p):
            if os.path.isfile(d):
                files.append(d)
            rec_glob("%s/*" % d, files)
    files = []
    rec_glob("%s/*" % mydir, files)
    extra_datas = []
    for f in files:
        extra_datas.append((f, f, 'DATA'))

    return extra_datas


block_cipher = None


# TODO: make dynamic hiddenimports append
a = Analysis(['riak_mesos/cli.py'],
             pathex=[os.getcwd(), 'env/lib/python2.7/site-packages', 'cli/env/lib/python2.7/site-packages'],
             binaries=None,
             datas=[],
             hiddenimports=['riak_mesos.commands.cmd_cluster',
                            'riak_mesos.commands.cmd_config',
                            'riak_mesos.commands.cmd_director',
                            'riak_mesos.commands.cmd_framework',
                            'riak_mesos.commands.cmd_node'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)


a.datas += extra_datas('riak_mesos/commands')


pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='riak-mesos',
          debug=False,
          strip=False,
          upx=True,
          console=True )
