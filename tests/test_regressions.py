def test_release_contract():
    import app
    assert hasattr(app,'tailnet_only_enabled')
    assert hasattr(app,'save_category_parent')
    assert hasattr(app,'category_selector_groups')

def test_no_auth_mode_does_not_redirect(appmod):
    appmod.set_setting("setup_complete","1")
    appmod.set_setting("tailnet_only","0")
    appmod.set_setting("auth_required","0")
    with appmod.app.test_client() as c:
        assert c.get("/", follow_redirects=False).status_code == 200

def test_auth_mode_redirects_without_session(appmod):
    appmod.set_setting("setup_complete","1")
    appmod.set_setting("tailnet_only","0")
    appmod.set_setting("auth_required","1")
    with appmod.app.test_client() as c:
        r=c.get("/", follow_redirects=False)
        assert r.status_code in (301,302)
        assert "/login" in r.headers["Location"]
