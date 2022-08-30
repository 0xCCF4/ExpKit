from expkit.base.architecture import Platform


def test_set():
    assert Platform.ALL.get_platforms() == [Platform.WINDOWS, Platform.LINUX, Platform.MACOS]