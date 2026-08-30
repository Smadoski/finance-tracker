from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


def test_postinstall_uses_packaged_version_without_release_hardcoding():
    script=(ROOT/'packaging/macos/scripts/postinstall').read_text()
    assert 'INSTALLED_VERSION=' in script
    assert 'EXPECTED_VERSION=' not in script
    assert '2.4.6' not in script


def test_macos_package_includes_offline_wheelhouse():
    script=(ROOT/'build-macos-pkg.sh').read_text()
    rsync_section=script.split('rsync -a',1)[1].split('chmod +x',1)[0]
    assert '--exclude wheelhouse' not in rsync_section
    assert 'pip download --dest "$WHEELHOUSE"' in script
    assert 'productbuild --package "$WORK/FinanceTracker-component.pkg" "$WORK/FinanceTracker-v${VERSION}-macOS.pkg"' in script
