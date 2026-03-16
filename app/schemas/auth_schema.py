from pydantic import BaseModel

class SignupSchema(BaseModel):

    email: str
    username: str
    password: str


class LoginSchema(BaseModel):

    email: str
    password: str