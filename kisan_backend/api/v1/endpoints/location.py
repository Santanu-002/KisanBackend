import json
import os
from fastapi import APIRouter, Depends
from kisan_backend.core.responses import SuccessResponse
from kisan_backend.schemas.location import LocationResponse

router = APIRouter(prefix="/locations", tags=["locations"])

# Path to the static JSON file
DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "core", "static", "locations.json"
)

# Cache data in memory after first load
_location_data = None

def get_location_data():
    global _location_data
    if _location_data is None:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                _location_data = json.load(f)
        else:
            _location_data = {"states": []}
    return _location_data

@router.get("/", response_model=LocationResponse)
async def get_locations():
    """
    Fetch the list of Indian states and their corresponding districts.
    """
    data = get_location_data()
    return SuccessResponse(
        message="Locations fetched successfully",
        data=data
    )
