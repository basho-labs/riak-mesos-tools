# -*- mode: python -*-


import os


block_cipher = None


# TODO: make dynamic hidden imports append
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
