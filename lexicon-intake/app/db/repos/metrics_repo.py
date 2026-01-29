"""Metrics repository for dashboard analytics."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, and_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import CallClassification, DeliveryStatus
from app.db.tables.lead_record import LeadRecord
from app.db.tables.delivery_record import DeliveryRecord
from app.db.tables.audit_log import AuditLog


class MetricsRepository:
    """Repository for dashboard metrics and analytics."""
    
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
    
    async def get_metrics_for_period(
        self,
        client_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Get overview metrics for a client within a date period.
        
        Args:
            client_id: Client identifier
            start_date: Start of period
            end_date: End of period
            
        Returns:
            Dictionary with total calls, booked jobs, revenue, conversion rate
        """
        # Total calls (all leads for client in period)
        total_calls_query = select(func.count(LeadRecord.id)).where(
            and_(
                LeadRecord.client_id == client_id,
                LeadRecord.created_at >= start_date,
                LeadRecord.created_at <= end_date,
            )
        )
        total_calls_result = await self.session.execute(total_calls_query)
        total_calls = total_calls_result.scalar() or 0
        
        # Booked jobs (qualified leads)
        booked_jobs_query = select(func.count(LeadRecord.id)).where(
            and_(
                LeadRecord.client_id == client_id,
                LeadRecord.classification == CallClassification.QUALIFIED.value,
                LeadRecord.created_at >= start_date,
                LeadRecord.created_at <= end_date,
            )
        )
        booked_jobs_result = await self.session.execute(booked_jobs_query)
        booked_jobs = booked_jobs_result.scalar() or 0
        
        # Revenue (estimated from qualified leads)
        # Using average job value of $500 for estimation
        avg_job_value = 500.0
        revenue = float(booked_jobs) * avg_job_value
        
        # Conversion rate
        conversion_rate = (float(booked_jobs) / float(total_calls) * 100) if total_calls > 0 else 0.0
        
        return {
            "total_calls": total_calls,
            "booked_jobs": booked_jobs,
            "revenue": revenue,
            "conversion_rate": round(conversion_rate, 2),
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            }
        }
    
    async def get_call_volume_by_day(
        self,
        client_id: str,
        days: int = 7,
    ) -> List[Dict[str, Any]]:
        """
        Get daily call volume for the last N days.
        
        Args:
            client_id: Client identifier
            days: Number of days to look back
            
        Returns:
            List of daily call volumes
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Group by day using date function
        call_volume_query = select(
            func.date(LeadRecord.created_at).label('date'),
            func.count(LeadRecord.id).label('call_count')
        ).where(
            and_(
                LeadRecord.client_id == client_id,
                LeadRecord.created_at >= start_date,
                LeadRecord.created_at <= end_date,
            )
        ).group_by(func.date(LeadRecord.created_at)).order_by('date')
        
        result = await self.session.execute(call_volume_query)
        rows = result.all()
        
        # Convert to list of dictionaries
        call_volumes = []
        for row in rows:
            call_volumes.append({
                "date": row.date.isoformat(),
                "call_count": row.call_count,
            })
        
        return call_volumes
    
    async def get_revenue_by_service_type(
        self,
        client_id: str,
        period: str = "30d",
    ) -> List[Dict[str, Any]]:
        """
        Get revenue breakdown by service type.
        
        Args:
            client_id: Client identifier
            period: Time period ("7d", "30d", "90d")
            
        Returns:
            List of revenue by service type
        """
        # Calculate date range
        days_map = {"7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(period, 30)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get qualified leads by service type
        revenue_query = select(
            LeadRecord.service_requested,
            func.count(LeadRecord.id).label('qualified_count')
        ).where(
            and_(
                LeadRecord.client_id == client_id,
                LeadRecord.classification == CallClassification.QUALIFIED.value,
                LeadRecord.created_at >= start_date,
                LeadRecord.created_at <= end_date,
                LeadRecord.service_requested.isnot(None),
            )
        ).group_by(LeadRecord.service_requested).order_by(desc('qualified_count'))
        
        result = await self.session.execute(revenue_query)
        rows = result.all()
        
        # Calculate revenue (using service-specific estimates)
        service_revenue_map = {
            "plumbing": 450.0,
            "hvac": 600.0,
            "electrical": 500.0,
            "roofing": 800.0,
            "landscaping": 300.0,
            "cleaning": 250.0,
            "painting": 400.0,
            "general": 350.0,
        }
        
        revenue_breakdown = []
        for row in rows:
            service_type = row.service_requested or "unknown"
            qualified_count = row.qualified_count
            avg_value = service_revenue_map.get(service_type.lower(), 350.0)
            revenue = float(qualified_count) * avg_value
            
            revenue_breakdown.append({
                "service_type": service_type,
                "qualified_count": qualified_count,
                "revenue": revenue,
                "avg_job_value": avg_value,
            })
        
        return revenue_breakdown
    
    async def get_conversion_funnel(
        self,
        client_id: str,
        period: str = "30d",
    ) -> Dict[str, Any]:
        """
        Get conversion funnel data.
        
        Args:
            client_id: Client identifier
            period: Time period ("7d", "30d", "90d")
            
        Returns:
            Conversion funnel data
        """
        # Calculate date range
        days_map = {"7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(period, 30)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Total calls (all leads)
        total_calls_query = select(func.count(LeadRecord.id)).where(
            and_(
                LeadRecord.client_id == client_id,
                LeadRecord.created_at >= start_date,
                LeadRecord.created_at <= end_date,
            )
        )
        total_calls_result = await self.session.execute(total_calls_query)
        total_calls = total_calls_result.scalar() or 0
        
        # Answered calls (assuming all leads are answered for now)
        answered_calls = total_calls  # Simplified assumption
        
        # Appointments (qualified leads)
        appointments_query = select(func.count(LeadRecord.id)).where(
            and_(
                LeadRecord.client_id == client_id,
                LeadRecord.classification == CallClassification.QUALIFIED.value,
                LeadRecord.created_at >= start_date,
                LeadRecord.created_at <= end_date,
            )
        )
        appointments_result = await self.session.execute(appointments_query)
        appointments = appointments_result.scalar() or 0
        
        # Completed jobs (delivered qualified leads)
        completed_jobs_query = select(func.count(DeliveryRecord.id)).join(
            LeadRecord, DeliveryRecord.lead_id == LeadRecord.lead_id
        ).where(
            and_(
                LeadRecord.client_id == client_id,
                LeadRecord.classification == CallClassification.QUALIFIED.value,
                DeliveryRecord.status == DeliveryStatus.SENT.value,
                LeadRecord.created_at >= start_date,
                LeadRecord.created_at <= end_date,
            )
        )
        completed_jobs_result = await self.session.execute(completed_jobs_query)
        completed_jobs = completed_jobs_result.scalar() or 0
        
        # Calculate conversion rates
        answer_rate = (float(answered_calls) / float(total_calls) * 100) if total_calls > 0 else 0.0
        appointment_rate = (float(appointments) / float(answered_calls) * 100) if answered_calls > 0 else 0.0
        completion_rate = (float(completed_jobs) / float(appointments) * 100) if appointments > 0 else 0.0
        
        return {
            "funnel": {
                "calls": total_calls,
                "answered": answered_calls,
                "appointments": appointments,
                "completed": completed_jobs,
            },
            "rates": {
                "answer_rate": round(answer_rate, 2),
                "appointment_rate": round(appointment_rate, 2),
                "completion_rate": round(completion_rate, 2),
            },
            "period": period,
        }
    
    async def get_recent_calls(
        self,
        client_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Get recent call logs for a client.
        
        Args:
            client_id: Client identifier
            limit: Number of records to return
            offset: Pagination offset
            
        Returns:
            Paginated call logs
        """
        # Get total count
        total_count_query = select(func.count(LeadRecord.id)).where(
            LeadRecord.client_id == client_id
        )
        total_count_result = await self.session.execute(total_count_query)
        total_count = total_count_result.scalar() or 0
        
        # Get recent calls
        calls_query = select(LeadRecord).where(
            LeadRecord.client_id == client_id
        ).order_by(desc(LeadRecord.created_at)).limit(limit).offset(offset)
        
        result = await self.session.execute(calls_query)
        calls = result.scalars().all()
        
        # Convert to dictionaries
        call_logs = []
        for call in calls:
            call_logs.append({
                "id": str(call.id),
                "lead_id": call.lead_id,
                "caller_phone": call.caller_phone,
                "caller_name": call.caller_name,
                "service_requested": call.service_requested,
                "urgency": call.urgency.value if call.urgency else None,
                "classification": call.classification.value if call.classification else None,
                "created_at": call.created_at.isoformat(),
                "budget": call.budget,
                "location_zip": call.location_zip,
            })
        
        return {
            "calls": call_logs,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count,
            }
        }
    
    async def get_ai_summaries(
        self,
        client_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Get AI-generated call summaries.
        
        Args:
            client_id: Client identifier
            limit: Number of records to return
            offset: Pagination offset
            
        Returns:
            Paginated AI summaries
        """
        # For now, return mock data since AI summaries aren't implemented yet
        # This would integrate with an AI service that processes call transcripts
        
        mock_summaries = [
            {
                "id": "summary-1",
                "lead_id": "lead-1",
                "summary": "Customer requested emergency plumbing repair for burst pipe. High urgency, budget flexible. Scheduled for same-day service.",
                "sentiment": "positive",
                "confidence": 0.92,
                "created_at": "2026-01-27T18:30:00Z",
            },
            {
                "id": "summary-2", 
                "lead_id": "lead-2",
                "summary": "Customer inquired about HVAC maintenance. Medium urgency, looking for quote. Follow-up scheduled.",
                "sentiment": "neutral",
                "confidence": 0.87,
                "created_at": "2026-01-27T17:45:00Z",
            },
            {
                "id": "summary-3",
                "lead_id": "lead-3", 
                "summary": "Electrical issue reported - flickering lights. Low urgency, customer comparison shopping.",
                "sentiment": "neutral",
                "confidence": 0.78,
                "created_at": "2026-01-27T16:20:00Z",
            },
        ]
        
        # Apply pagination
        total_count = len(mock_summaries)
        paginated_summaries = mock_summaries[offset:offset + limit]
        
        return {
            "summaries": paginated_summaries,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count,
            }
        }
