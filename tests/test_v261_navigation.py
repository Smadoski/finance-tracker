from html.parser import HTMLParser

import pytest


DESTINATIONS = [('/', 'Dashboard'), ('/accounts', 'Accounts'),
    ('/transactions', 'Transactions'), ('/quick', 'Quick Entry'),
    ('/pending', 'Pending'), ('/transfer', 'Transfer'),
    ('/categories', 'Categories'), ('/budgets/report', 'Targets'),
    ('/recurring/', 'Recurring'), ('/reports/categories', 'Reports'),
    ('/users', 'Users'), ('/settings', 'Settings'), ('/system', 'Status'),
    ('/valuations', 'Valuations')]


class Navigation(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.inside = False; self.links = []; self.menu = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'details' and attrs.get('class') == 'nav-menu': self.menu = attrs
        if tag == 'nav' and attrs.get('id') == 'primary-navigation': self.inside = True
        if tag == 'a' and self.inside: self.links.append(attrs)

    def handle_endtag(self, tag):
        if tag == 'nav': self.inside = False


@pytest.mark.parametrize('path,label', DESTINATIONS)
def test_all_destinations_load_have_navigation_and_active_state(appmod, path, label):
    appmod.set_setting('auth_required', '0'); appmod.set_setting('tailnet_only', '0')
    appmod.set_setting('backup_enabled', '0'); appmod.set_setting('fx_auto', '0')
    client = appmod.app.test_client()
    response = client.get(path)
    assert response.status_code == 200
    nav = Navigation(response.get_data(as_text=True))
    assert nav.menu is not None and 'open' in nav.menu  # desktop/no-JS safety
    assert {p for p, _ in DESTINATIONS} <= {a['href'] for a in nav.links}
    assert [a['href'] for a in nav.links if a.get('aria-current') == 'page'] == [path]
    assert client.get('/').status_code == 200


def test_breakpoint_and_native_menu_contract(appmod):
    appmod.set_setting('auth_required', '0'); appmod.set_setting('tailnet_only', '0')
    client = appmod.app.test_client()
    html = client.get('/').get_data(as_text=True)
    css = client.get('/static/style.css').get_data(as_text=True)
    assert 'aria-controls="primary-navigation"' in html and '☰ Menu' in html
    assert "window.matchMedia('(min-width: 901px)')" in html
    assert "addEventListener('change', syncNavigation)" in html
    assert "navigation.open = desktopNavigation.matches" in html
    assert "event.target.closest('a')" in html and "event.key === 'Escape'" in html
    assert '@media(max-width:900px)' in css and '@media(min-width:901px)' in css
    assert 'grid-template-columns:repeat(2,minmax(0,1fr))' in css
    # During resize, CSS can update before the matchMedia event. Keep a control
    # visible until native details is actually open, including fractional widths.
    assert '@media(min-width:901px){.nav-menu[open]>summary{display:none}' in css


@pytest.mark.parametrize('role', ['member', 'readonly'])
def test_admin_links_remain_role_restricted(appmod, role):
    appmod.set_setting('auth_required','1'); appmod.set_setting('tailnet_only','0')
    conn=appmod.db()
    uid=conn.execute('INSERT INTO users(name,username,password_hash,role) VALUES(?,?,?,?)',
        ('Navigation test', role, 'unused', role)).lastrowid
    conn.commit(); conn.close()
    client=appmod.app.test_client()
    with client.session_transaction() as session:
        session['user_id']=uid; session['auth_version']=1
    nav=Navigation(client.get('/').get_data(as_text=True))
    links={a['href'] for a in nav.links}
    assert not {'/users','/settings','/system'} & links
    assert '/logout' in links
