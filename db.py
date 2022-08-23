import motor.motor_asyncio

client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://root:toor@mongo:27017')
db = client.vote_bot
# {uid: int, stage: int, lang: str, certnum: str, tokens: [{}], template_stage: int, tokens_num: int, 't_*': str,
# 'o_*': str, get_queue: int, leave_queue: int, opt_reg: bool, opt_reg_completed: False}
users = db.users
votes = db.votes
