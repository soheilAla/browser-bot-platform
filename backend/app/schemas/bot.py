from pydantic import BaseModel


class BotResponse(BaseModel):
    bot_id: str
    name: str

    model_config = {"from_attributes": True}
