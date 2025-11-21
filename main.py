import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Property

app = FastAPI(title="Real Estate API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Real Estate API is running"}


class PropertyResponse(BaseModel):
    id: str
    title: str
    status: str
    price: int
    currency: str
    address: str
    city: str
    state: Optional[str]
    country: str
    bedrooms: int
    bathrooms: float
    property_type: str
    area_sqft: Optional[int]
    lot_size_sqft: Optional[int]
    year_built: Optional[int]
    parking_spaces: Optional[int]
    hoa_fee: Optional[int]
    description: Optional[str]
    images: List[str]
    features: List[str]


@app.get("/properties", response_model=List[PropertyResponse])
def list_properties(
    q: Optional[str] = Query(None, description="Full-text search across title, city, state"),
    min_price: Optional[int] = Query(None, ge=0),
    max_price: Optional[int] = Query(None, ge=0),
    bedrooms: Optional[int] = Query(None, ge=0),
    bathrooms: Optional[float] = Query(None, ge=0),
    city: Optional[str] = None,
    state: Optional[str] = None,
    property_type: Optional[str] = None,
    status: str = Query("sale", description="sale or rent"),
    limit: int = Query(50, ge=1, le=200),
):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    filter_query = {"status": status}

    if q:
        filter_query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"city": {"$regex": q, "$options": "i"}},
            {"state": {"$regex": q, "$options": "i"}},
            {"address": {"$regex": q, "$options": "i"}},
        ]

    if min_price is not None or max_price is not None:
        price_filter = {}
        if min_price is not None:
            price_filter["$gte"] = min_price
        if max_price is not None:
            price_filter["$lte"] = max_price
        filter_query["price"] = price_filter

    if bedrooms is not None:
        filter_query["bedrooms"] = {"$gte": bedrooms}

    if bathrooms is not None:
        filter_query["bathrooms"] = {"$gte": bathrooms}

    if city:
        filter_query["city"] = {"$regex": f"^{city}$", "$options": "i"}

    if state:
        filter_query["state"] = {"$regex": f"^{state}$", "$options": "i"}

    if property_type:
        filter_query["property_type"] = {"$regex": f"^{property_type}$", "$options": "i"}

    docs = db["property"].find(filter_query).limit(limit)

    results: List[PropertyResponse] = []
    for d in docs:
        results.append(
            PropertyResponse(
                id=str(d.get("_id")),
                title=d.get("title"),
                status=d.get("status"),
                price=d.get("price"),
                currency=d.get("currency", "USD"),
                address=d.get("address"),
                city=d.get("city"),
                state=d.get("state"),
                country=d.get("country", "USA"),
                bedrooms=d.get("bedrooms", 0),
                bathrooms=d.get("bathrooms", 0.0),
                property_type=d.get("property_type", "house"),
                area_sqft=d.get("area_sqft"),
                lot_size_sqft=d.get("lot_size_sqft"),
                year_built=d.get("year_built"),
                parking_spaces=d.get("parking_spaces"),
                hoa_fee=d.get("hoa_fee"),
                description=d.get("description"),
                images=d.get("images", []),
                features=d.get("features", []),
            )
        )

    return results


@app.post("/properties", response_model=str)
def create_property(payload: Property):
    inserted_id = create_document("property", payload)
    return inserted_id


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
