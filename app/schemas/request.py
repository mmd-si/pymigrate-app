from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class LoginRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    username: str
    password: str
    remember_me: bool

class TransferRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    row_ids: list[str]
