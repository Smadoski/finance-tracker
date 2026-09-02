def no_auth(appmod):
    appmod.set_setting('tailnet_only', '0')
    appmod.set_setting('auth_required', '0')


def page(client, path):
    response = client.get(path)
    assert response.status_code == 200
    return response.data


def test_shared_progressive_disclosure_and_responsive_contract(appmod):
    no_auth(appmod)
    client = appmod.app.test_client()
    css = page(client, '/static/style.css')
    for token in (b'.disclosure', b'.manage-panel', b'.filter-panel',
                  b'.settings-panel', b'.mobile-cards', b':focus-visible'):
        assert token in css
    assert b'@media(max-width:700px)' in css


def test_add_forms_are_collapsed_and_quick_entry_stays_immediate(appmod):
    no_auth(appmod)
    client = appmod.app.test_client()
    for path, label in (
        ('/accounts', b'+ Add account'),
        ('/transactions', b'+ Add transaction'),
        ('/budgets/', b'+ Add target'),
        ('/recurring/', b'+ Add recurring transaction'),
        ('/valuations', b'+ Record valuation'),
    ):
        data = page(client, path)
        assert b'class="disclosure"' in data and label in data
    quick = page(client, '/quick')
    assert b'name="description"' in quick and b'Save pending' in quick


def test_management_filters_settings_and_navigation_are_compact(appmod):
    no_auth(appmod)
    client = appmod.app.test_client()
    assert b'class="nav-menu"' in page(client, '/')
    assert b'Report options' in page(client, '/budgets/report')
    settings = page(client, '/settings')
    for heading in (b'Application preferences', b'Security and Tailnet',
                    b'Local backups', b'Dropbox', b'Licence Configuration'):
        assert heading in settings
    assert settings.count(b'class="settings-panel"') >= 5


def test_version_and_information_architecture(appmod):
    no_auth(appmod)
    client = appmod.app.test_client()
    assert appmod.APP_VERSION == '2.6.0'
    status = page(client, '/system')
    settings = page(client, '/settings')
    assert b'2.6.0' in status and b'Licensed To' in status
    assert b'Licence Configuration' in settings
    assert b'Information</h2>' not in settings
