# api/routes/financial_intelligence.py

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_
from datetime import datetime, timedelta
from storage.db.database import SessionLocal
from storage.models.monthly_spending_summary import MonthlySpendingSummary
from storage.models.monthly_category_spend import MonthlyCategorySpend
from storage.models.monthly_category_trend import MonthlyCategoryTrend
from storage.models.financial_event import FinancialEvent

router = APIRouter(
    prefix="/financial",
    tags=["Financial Intelligence"]
)


@router.get("/summary")
async def get_financial_summary():
    """
    Returns a list of monthly spending summaries.
    """
    db = SessionLocal()
    try:
        summaries = db.query(MonthlySpendingSummary).order_by(MonthlySpendingSummary.month_key.desc()).all()
        result = []
        for s in summaries:
            try:
                month_name = datetime.strptime(s.month_key, "%Y-%m").strftime("%B %Y")
            except Exception:
                month_name = s.month_key

            result.append({
                "summary_id": s.summary_id,
                "month_key": s.month_key,
                "month": month_name,
                "total_spend": s.total_spend,
                "transaction_count": s.transaction_count
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/categories")
async def get_category_breakdown(month_key: str = Query(..., description="Month key in YYYY-MM format")):
    """
    Returns the category spending breakdown for a specific month.
    """
    db = SessionLocal()
    try:
        spends = db.query(MonthlyCategorySpend).filter(
            MonthlyCategorySpend.month_key == month_key
        ).all()
        return [
            {
                "entry_id": s.entry_id,
                "month_key": s.month_key,
                "category_name": s.category_name,
                "amount": s.amount,
                "transaction_count": s.transaction_count
            }
            for s in spends
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/trends")
async def get_monthly_trends(month_key: str = Query(..., description="Month key in YYYY-MM format")):
    """
    Returns category spending MoM trends for a given month.
    """
    db = SessionLocal()
    try:
        trends = db.query(MonthlyCategoryTrend).filter(
            MonthlyCategoryTrend.month_key == month_key
        ).all()
        return [
            {
                "trend_id": t.trend_id,
                "month_key": t.month_key,
                "category_name": t.category_name,
                "current_amount": t.current_amount,
                "previous_amount": t.previous_amount,
                "change_percentage": t.change_percentage
            }
            for t in trends
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/drilldown")
async def get_category_drilldown(
    month_key: str = Query(..., description="Month key in YYYY-MM format"),
    category_name: str = Query(..., description="Name of the spending category")
):
    """
    Returns individual financial transaction events for a specific category within a month.
    """
    db = SessionLocal()
    try:
        start_date = datetime.strptime(month_key, "%Y-%m")
        if start_date.month == 12:
            end_date = datetime(start_date.year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_date = datetime(start_date.year, start_date.month + 1, 1) - timedelta(seconds=1)

        events = db.query(FinancialEvent).filter(
            and_(
                FinancialEvent.event_date >= start_date,
                FinancialEvent.event_date <= end_date,
                FinancialEvent.category == category_name,
                FinancialEvent.transaction_type == "debit"
            )
        ).all()

        return [
            {
                "id": e.id,
                "title": e.title,
                "amount": e.amount,
                "currency": e.currency,
                "transaction_type": e.transaction_type,
                "payment_channel": e.payment_channel,
                "paid_to": e.paid_to,
                "event_date": e.event_date.isoformat() if e.event_date else None,
                "category": e.category
            }
            for e in events
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
