from nicegui import ui
from nicegui.testing import User

async def test_mainpage(user: User):
    await user.open("/")

