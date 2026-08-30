import os, sys, importlib, shutil
import pytest

@pytest.fixture()
def appmod(tmp_path, monkeypatch):
    source=os.path.dirname(os.path.dirname(__file__))
    sandbox=tmp_path/'app'
    shutil.copytree(source,sandbox,ignore=shutil.ignore_patterns('data','.venv','__pycache__'))
    monkeypatch.syspath_prepend(str(sandbox))
    old=os.getcwd(); os.chdir(sandbox); sys.modules.pop('app',None)
    try:
        module=importlib.import_module('app')
        module.app.config.update(TESTING=True,SECRET_KEY='test')
        module.set_setting('setup_complete','1')
        yield module
    finally:
        os.chdir(old); sys.modules.pop('app',None)
