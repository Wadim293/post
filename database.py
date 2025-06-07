from tortoise import Tortoise, fields
from tortoise.models import Model

class InviteLink(Model):
    id = fields.IntField(pk=True)
    ref = fields.CharField(max_length=255, unique=True)
    link = fields.CharField(max_length=255)

class UserMessageLog(Model):
    id = fields.IntField(pk=True)
    telegram_id = fields.BigIntField(unique=True)

class VisitStats(Model):
    id = fields.IntField(pk=True)
    ref = fields.CharField(max_length=255)
    visited = fields.BooleanField(default=False)
    clicked = fields.BooleanField(default=False)
    joined = fields.BooleanField(default=False)

class GreetingText(Model):
    id = fields.IntField(pk=True)
    text = fields.TextField()
    enabled = fields.BooleanField(default=True)

async def init_db():
    await Tortoise.init(
        db_url="sqlite://db.sqlite3",
        modules={"models": ["database"]}
    )
    await Tortoise.generate_schemas()