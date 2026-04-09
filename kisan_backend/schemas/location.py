from pydantic import BaseModel
from typing import List

class StateData(BaseModel):
    state: str
    districts: List[str]

class LocationResponse(BaseModel):
    states: List[StateData]
