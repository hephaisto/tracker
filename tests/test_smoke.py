from nicegui import ui
from nicegui.testing import User

async def test_mainpage(user: User):
    await user.open("/")
    await user.should_see("python-podman-dependabot-test")

