from fastapi import FastAPI, Depends, HTTPException, status
from google.cloud import bigquery
from pydantic import BaseModel
from datetime import date
from typing import Optional

app = FastAPI()

PROJECT_ID = "mgmt545project-carls171"
DATASET = "property_mgmt"

# CORS middleware tells the browser which cross-origin requests are allowed.
# Allowing all origins ("*") is fine for a classroom demo but should be
# restricted to specific domains in a real production application.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # accept requests from any origin
    allow_methods=["GET", "POST"],
    allow_headers=["*"],       # accept any request headers
)

# ---------------------------------------------------------------------------
# Dependency: BigQuery client
# ---------------------------------------------------------------------------

def get_bq_client():
    client = bigquery.Client()
    try:
        yield client
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

@app.get("/properties")
def get_properties(bq: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        SELECT
            property_id,
            name,
            address,
            city,
            state,
            postal_code,
            property_type,
            tenant_name,
            monthly_rent
        FROM `{PROJECT_ID}.{DATASET}.properties`
        ORDER BY property_id
    """

    try:
        results = bq.query(query).result()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {str(e)}"
        )

    return [dict(row) for row in results]


@app.get("/properties/{property_id}")
def get_properties_byid(property_id: int, bq: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        SELECT
            property_id,
            name,
            address,
            city,
            state,
            postal_code,
            property_type,
            tenant_name,
            monthly_rent
        FROM `{PROJECT_ID}.{DATASET}.properties`
        WHERE property_id = @property_id
        LIMIT 1
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("property_id", "INT64", property_id)
        ]
    )

    try:
        results = bq.query(query, job_config=job_config).result()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {str(e)}"
        )

    properties = [dict(row) for row in results]

    if not properties:
        raise HTTPException(
            status_code=404,
            detail="Property not found. Try another number."
        )

    return properties[0]


# ---------------------------------------------------------------------------
# Income
# ---------------------------------------------------------------------------

@app.get("/income/{property_id}")
def get_income_byid(property_id: int, bq: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        SELECT
            income_id,
            property_id,
            amount,
            date,
            description
        FROM `{PROJECT_ID}.{DATASET}.income`
        WHERE property_id = @property_id
        ORDER BY date DESC
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("property_id", "INT64", property_id)
        ]
    )

    try:
        results = bq.query(query, job_config=job_config).result()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {str(e)}"
        )

    income = [dict(row) for row in results]

    if not income:
        raise HTTPException(
            status_code=404,
            detail="No income records found."
        )

    return income


class IncomeCreate(BaseModel):
    amount: float
    date: date
    description: str


@app.post("/income/{property_id}")
def create_income_record(
    property_id: int,
    income: IncomeCreate,
    bq: bigquery.Client = Depends(get_bq_client)
):
    query = f"""
        INSERT INTO `{PROJECT_ID}.{DATASET}.income`
            (property_id, amount, date, description)
        VALUES
            (@property_id, @amount, @date, @description)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("property_id", "INT64", property_id),
            bigquery.ScalarQueryParameter("amount", "FLOAT64", income.amount),
            bigquery.ScalarQueryParameter("date", "DATE", income.date.isoformat()),
            bigquery.ScalarQueryParameter("description", "STRING", income.description),
        ]
    )

    try:
        bq.query(query, job_config=job_config).result()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {str(e)}"
        )

    return {
        "message": "Income record created successfully.",
        "property_id": property_id,
        "amount": income.amount,
        "date": income.date,
        "description": income.description
    }


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------

@app.get("/expenses/{property_id}")
def get_expenses_byid(property_id: int, bq: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        SELECT
            expense_id,
            property_id,
            amount,
            date,
            description
        FROM `{PROJECT_ID}.{DATASET}.expenses`
        WHERE property_id = @property_id
        ORDER BY date DESC
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("property_id", "INT64", property_id)
        ]
    )

    try:
        results = bq.query(query, job_config=job_config).result()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {str(e)}"
        )

    expense = [dict(row) for row in results]

    if not expense:
        raise HTTPException(
            status_code=404,
            detail="No expense records found."
        )

    return expense


# -----------------------------
# Request Model
# -----------------------------
class ExpenseCreate(BaseModel):
    amount: float
    date: date
    category: str
    vendor: str
    description: str


# -----------------------------
# Create Expense Endpoint
# -----------------------------
@app.post("/expenses/{property_id}")
def create_expense_record(
    property_id: int,
    expense: ExpenseCreate,
    bq: bigquery.Client = Depends(get_bq_client)
):
    query = f"""
        INSERT INTO `{PROJECT_ID}.{DATASET}.expenses`
        (property_id, amount, date, category, vendor, description)
        VALUES
        (@property_id, @amount, @date, @category, @vendor, @description)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("property_id", "INT64", property_id),
            bigquery.ScalarQueryParameter("amount", "FLOAT64", expense.amount),
            
            # ✅ FIXED: pass date directly (NOT isoformat)
            bigquery.ScalarQueryParameter("date", "DATE", expense.date),
            
            bigquery.ScalarQueryParameter("category", "STRING", expense.category),
            bigquery.ScalarQueryParameter("vendor", "STRING", expense.vendor),
            bigquery.ScalarQueryParameter("description", "STRING", expense.description),
        ]
    )

    try:
        job = bq.query(query, job_config=job_config)
        job.result()  # Wait for completion

    except Exception as e:
        # ✅ MUCH better debugging
        print("=== BIGQUERY ERROR ===")
        print(str(e))
        print("======================")

        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {str(e)}"
        )

    return {
        "message": "Expense record created successfully.",
        "property_id": property_id,
        "amount": expense.amount,
        "date": expense.date,
        "category": expense.category,
        "vendor": expense.vendor,
        "description": expense.description
    }

# ---------------------------------------------------------------------------
# Additional
# ---------------------------------------------------------------------------
@app.get("/netincome/{property_id}")
def get_net_income(property_id: int, bq: bigquery.Client = Depends(get_bq_client)):
    """
    Returns the net income (income - expenses) for a property.
    """

    query = f"""
        SELECT
            IFNULL(SUM(i.amount), 0) AS total_income,
            IFNULL(SUM(e.amount), 0) AS total_expenses,
            IFNULL(SUM(i.amount), 0) - IFNULL(SUM(e.amount), 0) AS net_income
        FROM `{PROJECT_ID}.{DATASET}.properties` p
        LEFT JOIN `{PROJECT_ID}.{DATASET}.income` i
            ON p.property_id = i.property_id
        LEFT JOIN `{PROJECT_ID}.{DATASET}.expenses` e
            ON p.property_id = e.property_id
        WHERE p.property_id = @property_id
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("property_id", "INT64", property_id)
        ]
    )

    try:
        results = bq.query(query, job_config=job_config).result()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {str(e)}"
        )

    rows = [dict(row) for row in results]

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Property not found."
        )

    return {
        "property_id": property_id,
        "total_income": rows[0]["total_income"],
        "total_expenses": rows[0]["total_expenses"],
        "net_income": rows[0]["net_income"]
    }


class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    property_type: Optional[str] = None
    tenant_name: Optional[str] = None
    monthly_rent: Optional[float] = None

@app.put("/properties/{property_id}")
def update_property(
    property_id: int,
    property: PropertyUpdate,
    bq: bigquery.Client = Depends(get_bq_client)
):
    """
    Updates an existing property.
    """

    update_fields = []
    query_params = [
        bigquery.ScalarQueryParameter("property_id", "INT64", property_id)
    ]

    # Build dynamic update query
    if property.name is not None:
        update_fields.append("name = @name")
        query_params.append(bigquery.ScalarQueryParameter("name", "STRING", property.name))

    if property.address is not None:
        update_fields.append("address = @address")
        query_params.append(bigquery.ScalarQueryParameter("address", "STRING", property.address))

    if property.city is not None:
        update_fields.append("city = @city")
        query_params.append(bigquery.ScalarQueryParameter("city", "STRING", property.city))

    if property.state is not None:
        update_fields.append("state = @state")
        query_params.append(bigquery.ScalarQueryParameter("state", "STRING", property.state))

    if property.postal_code is not None:
        update_fields.append("postal_code = @postal_code")
        query_params.append(bigquery.ScalarQueryParameter("postal_code", "STRING", property.postal_code))

    if property.property_type is not None:
        update_fields.append("property_type = @property_type")
        query_params.append(bigquery.ScalarQueryParameter("property_type", "STRING", property.property_type))

    if property.tenant_name is not None:
        update_fields.append("tenant_name = @tenant_name")
        query_params.append(bigquery.ScalarQueryParameter("tenant_name", "STRING", property.tenant_name))

    if property.monthly_rent is not None:
        update_fields.append("monthly_rent = @monthly_rent")
        query_params.append(bigquery.ScalarQueryParameter("monthly_rent", "FLOAT64", property.monthly_rent))

    if not update_fields:
        raise HTTPException(
            status_code=422,
            detail="No fields provided for update."
        )

    query = f"""
        UPDATE `{PROJECT_ID}.{DATASET}.properties`
        SET {", ".join(update_fields)}
        WHERE property_id = @property_id
    """

    job_config = bigquery.QueryJobConfig(query_parameters=query_params)

    try:
        bq.query(query, job_config=job_config).result()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {str(e)}"
        )

    return {
        "message": "Property updated successfully.",
        "property_id": property_id
    }

class PropertyCreate(BaseModel):
    name: str
    address: str
    city: str
    state: str
    postal_code: str
    property_type: str
    tenant_name: str
    monthly_rent: float

@app.post("/properties")
def create_property(
    property: PropertyCreate,
    bq: bigquery.Client = Depends(get_bq_client)
):
    """
    Creates a new property.
    """

    query = f"""
        INSERT INTO `{PROJECT_ID}.{DATASET}.properties`
            (name, address, city, state, postal_code, property_type, tenant_name, monthly_rent)
        VALUES
            (@name, @address, @city, @state, @postal_code, @property_type, @tenant_name, @monthly_rent)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("name", "STRING", property.name),
            bigquery.ScalarQueryParameter("address", "STRING", property.address),
            bigquery.ScalarQueryParameter("city", "STRING", property.city),
            bigquery.ScalarQueryParameter("state", "STRING", property.state),
            bigquery.ScalarQueryParameter("postal_code", "STRING", property.postal_code),
            bigquery.ScalarQueryParameter("property_type", "STRING", property.property_type),
            bigquery.ScalarQueryParameter("tenant_name", "STRING", property.tenant_name),
            bigquery.ScalarQueryParameter("monthly_rent", "FLOAT64", property.monthly_rent),
        ]
    )

    try:
        bq.query(query, job_config=job_config).result()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {str(e)}"
        )

    return {
        "message": "Property created successfully.",
        "property": property
    }


@app.delete("/properties/{property_id}/income/{income_id}")
def delete_income_for_property(
    property_id: int,
    income_id: int,
    bq: bigquery.Client = Depends(get_bq_client)
):
    """
    Deletes a specific income record for a specific property.
    """

    query = f"""
        DELETE FROM `{PROJECT_ID}.{DATASET}.income`
        WHERE income_id = @income_id 
          AND property_id = @property_id
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("income_id", "INT64", income_id),
            bigquery.ScalarQueryParameter("property_id", "INT64", property_id)
        ]
    )

    try:
        job = bq.query(query, job_config=job_config)
        job.result() 
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {str(e)}"
        )

    return {
        "message": "Income record deletion processed.",
        "income_id": income_id,
        "property_id": property_id
    }