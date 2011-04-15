import sys

from _newrelic import *

sys.meta_path.insert(0, ImportHookFinder())

def _hook(hook_module_name):
    def _instrument(module):
        hook_module = __import__(hook_module_name)
        for name in hook_module_name.split('.')[1:]:
            hook_module = getattr(hook_module, name)
        hook_module.instrument(module)
    return _instrument

register_import_hook('django', _hook('newrelic.framework_django'))
register_import_hook('flask', _hook('newrelic.framework_flask'))

register_import_hook('gluon.compileapp', _hook('newrelic.framework_web2py'))
register_import_hook('gluon.main', _hook('newrelic.framework_web2py'))

register_import_hook('cx_Oracle', _hook('newrelic.database_dbapi2'))
register_import_hook('MySQLdb', _hook('newrelic.database_dbapi2'))
register_import_hook('psycopg', _hook('newrelic.database_dbapi2'))
register_import_hook('psycopg2', _hook('newrelic.database_dbapi2'))
register_import_hook('pysqlite2', _hook('newrelic.database_dbapi2'))
register_import_hook('sqlite3', _hook('newrelic.database_dbapi2'))

register_import_hook('jinja2', _hook('newrelic.template_jinja2'))

register_import_hook('feedparser', _hook('newrelic.external_feedparser'))
