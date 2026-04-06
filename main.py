from fastapi import FastAPI, Depends, HTTPException, status
from google.cloud import bigquery

app = FastAPI()

PROJECT_ID = "sturdy-pivot-474513-f1"
DATASET = "property_mgmt"


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
    """
    Returns all properties in the database.
    """
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)}"
        )

    properties = [dict(row) for row in results]
    return properties


@app.get("/properties/{property_id}")
def get_properties_byid(property_id: int, bq: bigquery.Client = Depends(get_bq_client)):
    """
    Returns a single property by ID.
    """
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
    """
    Returns all income records for a property.
    """
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
        results = results = bq.query(query, job_config=job_config).result()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)}"
        )

    income = [dict(row) for row in results]
    
    if not income:
        raise HTTPException(
            status_code=404,
            detail="No income records found."
        )
    return income


@app.post("/income/{property_id}")
def create_income_record(property_id: int, bq: bigquery.Client = Depends(get_bq_client)):
    """
    Creates a new income record for a property.
    """
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
        results = results = bq.query(query, job_config=job_config).result()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
    """
    Returns all expenses for a property.
    """
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
        results = results = bq.query(query, job_config=job_config).result()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)}"
        )

    expense = [dict(row) for row in results]
    
    if not expense:
        raise HTTPException(
            status_code=404,
            detail="No expense records found."
        )
    return expense



@app.post("/expenses/{property_id}")
def create_expense_record(property_id: int, bq: bigquery.Client = Depends(get_bq_client)):
    """
    Creates a new expense record for a property.
    """
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
            bigquery.ScalarQueryParameter("date", "DATE", expense.date.isoformat()),
            bigquery.ScalarQueryParameter("category", "STRING", expense.category),
            bigquery.ScalarQueryParameter("vendor", "STRING", expense.vendor),
            bigquery.ScalarQueryParameter("description", "STRING", expense.description),
        ]
    )

    try:
        results = results = bq.query(query, job_config=job_config).result()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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