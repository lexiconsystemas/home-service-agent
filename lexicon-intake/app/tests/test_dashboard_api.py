"""Tests for dashboard API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers.dashboard import verify_client_api_key
from app.db.repos.metrics_repo import MetricsRepository


class TestDashboardAPI:
    """Test dashboard API endpoints."""
    
    @pytest.mark.asyncio
    async def test_verify_client_api_key_success(self):
        """Test successful client API key verification."""
        with patch('app.api.routers.dashboard.AuthService.extract_client_id_from_api_key') as mock_extract:
            mock_extract.return_value = "test-client-123"
            
            request = MagicMock()
            request.headers = {"X-Client-API-Key": "lexicon_client_test-client-123_abc123"}
            
            result = await verify_client_api_key(request)
            
            assert result == "test-client-123"
            mock_extract.assert_called_once_with("lexicon_client_test-client-123_abc123")
    
    @pytest.mark.asyncio
    async def test_verify_client_api_key_missing(self):
        """Test missing client API key."""
        request = MagicMock()
        request.headers = {}
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_client_api_key(request)
        
        assert exc_info.value.status_code == 401
        assert "Client API key required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_verify_client_api_key_invalid(self):
        """Test invalid client API key."""
        with patch('app.api.routers.dashboard.AuthService.extract_client_id_from_api_key') as mock_extract:
            mock_extract.return_value = None
            
            request = MagicMock()
            request.headers = {"X-Client-API-Key": "invalid-key"}
            
            with pytest.raises(HTTPException) as exc_info:
                await verify_client_api_key(request)
            
            assert exc_info.value.status_code == 401
            assert "Invalid client API key" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_dashboard_metrics(self):
        """Test GET /v1/dashboard/metrics endpoint."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_metrics_repo = AsyncMock()
        mock_metrics = {
            "total_calls": 150,
            "booked_jobs": 45,
            "revenue": 22500.0,
            "conversion_rate": 30.0,
        }
        mock_metrics_repo.get_metrics_for_period.return_value = mock_metrics
        
        request = MagicMock()
        request.headers = {"X-Client-API-Key": "lexicon_client_test-client-123_abc123"}
        
        with patch('app.api.routers.dashboard.MetricsRepository') as mock_repo_class:
            mock_repo_class.return_value = mock_metrics_repo
            
            from app.api.routers.dashboard import get_dashboard_metrics
            
            result = await get_dashboard_metrics(
                request=request,
                db=mock_session,
                client_id="test-client-123",
                period="30d"
            )
            
            assert result["success"] is True
            assert result["data"]["total_calls"] == 150
            assert result["data"]["booked_jobs"] == 45
            assert result["data"]["revenue"] == 22500.0
            assert result["data"]["conversion_rate"] == 30.0
    
    @pytest.mark.asyncio
    async def test_get_call_performance(self):
        """Test GET /v1/dashboard/call-performance endpoint."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_metrics_repo = AsyncMock()
        mock_call_volume = [
            {"date": "2026-01-27", "call_count": 25},
            {"date": "2026-01-26", "call_count": 30},
            {"date": "2026-01-25", "call_count": 20},
        ]
        mock_metrics_repo.get_call_volume_by_day.return_value = mock_call_volume
        
        request = MagicMock()
        request.headers = {"X-Client-API-Key": "lexicon_client_test-client-123_abc123"}
        
        with patch('app.api.routers.dashboard.MetricsRepository') as mock_repo_class:
            mock_repo_class.return_value = mock_metrics_repo
            
            from app.api.routers.dashboard import get_call_performance
            
            result = await get_call_performance(
                request=request,
                db=mock_session,
                client_id="test-client-123",
                days=7
            )
            
            assert result["success"] is True
            assert result["data"]["call_volume"] == mock_call_volume
            assert result["data"]["period_days"] == 7
    
    @pytest.mark.asyncio
    async def test_get_revenue_breakdown(self):
        """Test GET /v1/dashboard/revenue endpoint."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_metrics_repo = AsyncMock()
        mock_revenue_breakdown = [
            {"service_type": "plumbing", "qualified_count": 15, "revenue": 6750.0, "avg_job_value": 450.0},
            {"service_type": "hvac", "qualified_count": 10, "revenue": 6000.0, "avg_job_value": 600.0},
        ]
        mock_metrics_repo.get_revenue_by_service_type.return_value = mock_revenue_breakdown
        
        request = MagicMock()
        request.headers = {"X-Client-API-Key": "lexicon_client_test-client-123_abc123"}
        
        with patch('app.api.routers.dashboard.MetricsRepository') as mock_repo_class:
            mock_repo_class.return_value = mock_metrics_repo
            
            from app.api.routers.dashboard import get_revenue_breakdown
            
            result = await get_revenue_breakdown(
                request=request,
                db=mock_session,
                client_id="test-client-123",
                period="30d"
            )
            
            assert result["success"] is True
            assert result["data"]["revenue_breakdown"] == mock_revenue_breakdown
            assert result["data"]["total_revenue"] == 12750.0
            assert result["data"]["period"] == "30d"
    
    @pytest.mark.asyncio
    async def test_get_conversion_funnel(self):
        """Test GET /v1/dashboard/funnel endpoint."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_metrics_repo = AsyncMock()
        mock_funnel_data = {
            "funnel": {
                "calls": 150,
                "answered": 150,
                "appointments": 45,
                "completed": 40,
            },
            "rates": {
                "answer_rate": 100.0,
                "appointment_rate": 30.0,
                "completion_rate": 88.89,
            },
            "period": "30d",
        }
        mock_metrics_repo.get_conversion_funnel.return_value = mock_funnel_data
        
        request = MagicMock()
        request.headers = {"X-Client-API-Key": "lexicon_client_test-client-123_abc123"}
        
        with patch('app.api.routers.dashboard.MetricsRepository') as mock_repo_class:
            mock_repo_class.return_value = mock_metrics_repo
            
            from app.api.routers.dashboard import get_conversion_funnel
            
            result = await get_conversion_funnel(
                request=request,
                db=mock_session,
                client_id="test-client-123",
                period="30d"
            )
            
            assert result["success"] is True
            assert result["data"] == mock_funnel_data
    
    @pytest.mark.asyncio
    async def test_get_recent_calls(self):
        """Test GET /v1/dashboard/calls endpoint."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_metrics_repo = AsyncMock()
        mock_call_logs = {
            "calls": [
                {
                    "id": "call-1",
                    "lead_id": "lead-1",
                    "caller_phone": "+1234567890",
                    "caller_name": "John Doe",
                    "service_requested": "plumbing",
                    "urgency": "high",
                    "classification": "QUALIFIED_LEAD",
                    "created_at": "2026-01-27T18:30:00Z",
                    "budget": 500,
                    "location": "New York, NY",
                }
            ],
            "pagination": {
                "total": 1,
                "limit": 50,
                "offset": 0,
                "has_more": False,
            }
        }
        mock_metrics_repo.get_recent_calls.return_value = mock_call_logs
        
        request = MagicMock()
        request.headers = {"X-Client-API-Key": "lexicon_client_test-client-123_abc123"}
        
        with patch('app.api.routers.dashboard.MetricsRepository') as mock_repo_class:
            mock_repo_class.return_value = mock_metrics_repo
            
            from app.api.routers.dashboard import get_recent_calls
            
            result = await get_recent_calls(
                request=request,
                db=mock_session,
                client_id="test-client-123",
                limit=50,
                offset=0
            )
            
            assert result["success"] is True
            assert result["data"] == mock_call_logs
    
    @pytest.mark.asyncio
    async def test_get_ai_summaries(self):
        """Test GET /v1/dashboard/ai-summaries endpoint."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_metrics_repo = AsyncMock()
        mock_summaries = {
            "summaries": [
                {
                    "id": "summary-1",
                    "lead_id": "lead-1",
                    "summary": "Customer requested emergency plumbing repair for burst pipe.",
                    "sentiment": "positive",
                    "confidence": 0.92,
                    "created_at": "2026-01-27T18:30:00Z",
                }
            ],
            "pagination": {
                "total": 1,
                "limit": 20,
                "offset": 0,
                "has_more": False,
            }
        }
        mock_metrics_repo.get_ai_summaries.return_value = mock_summaries
        
        request = MagicMock()
        request.headers = {"X-Client-API-Key": "lexicon_client_test-client-123_abc123"}
        
        with patch('app.api.routers.dashboard.MetricsRepository') as mock_repo_class:
            mock_repo_class.return_value = mock_metrics_repo
            
            from app.api.routers.dashboard import get_ai_summaries
            
            result = await get_ai_summaries(
                request=request,
                db=mock_session,
                client_id="test-client-123",
                limit=20,
                offset=0
            )
            
            assert result["success"] is True
            assert result["data"] == mock_summaries
    
    @pytest.mark.asyncio
    async def test_get_business_profile(self):
        """Test GET /v1/dashboard/profile endpoint."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_client_repo = AsyncMock()
        mock_client_config = MagicMock()
        mock_client_config.client_id = "test-client-123"
        mock_client_config.business_name = "Test Plumbing"
        mock_client_config.phone = "+1234567890"
        mock_client_config.email = "test@example.com"
        mock_client_config.address = "123 Main St, New York, NY"
        mock_client_config.service_areas = ["New York", "Brooklyn"]
        mock_client_config.delivery_channels = ["SMS", "EMAIL"]
        mock_client_config.followup_flags = {"confirmation": True, "reminder": True}
        mock_client_config.created_at = datetime.utcnow()
        mock_client_config.updated_at = datetime.utcnow()
        
        mock_client_repo.get_by_client_id.return_value = mock_client_config
        
        request = MagicMock()
        request.headers = {"X-Client-API-Key": "lexicon_client_test-client-123_abc123"}
        
        with patch('app.api.routers.dashboard.ClientRepository') as mock_repo_class:
            mock_repo_class.return_value = mock_client_repo
            
            from app.api.routers.dashboard import get_business_profile
            
            result = await get_business_profile(
                request=request,
                db=mock_session,
                client_id="test-client-123"
            )
            
            assert result["success"] is True
            assert result["data"]["client_id"] == "test-client-123"
            assert result["data"]["business_name"] == "Test Plumbing"
            assert result["data"]["phone"] == "+1234567890"
    
    @pytest.mark.asyncio
    async def test_get_business_profile_not_found(self):
        """Test GET /v1/dashboard/profile endpoint with missing client."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_client_repo = AsyncMock()
        mock_client_repo.get_by_client_id.return_value = None
        
        request = MagicMock()
        request.headers = {"X-Client-API-Key": "lexicon_client_test-client-123_abc123"}
        
        with patch('app.api.routers.dashboard.ClientRepository') as mock_repo_class:
            mock_repo_class.return_value = mock_client_repo
            
            from app.api.routers.dashboard import get_business_profile
            
            with pytest.raises(HTTPException) as exc_info:
                await get_business_profile(
                    request=request,
                    db=mock_session,
                    client_id="test-client-123"
                )
            
            assert exc_info.value.status_code == 404
            assert "Client configuration not found" in str(exc_info.value.detail)


class TestMetricsRepository:
    """Test metrics repository methods."""
    
    @pytest.mark.asyncio
    async def test_get_metrics_for_period(self):
        """Test get_metrics_for_period method."""
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock query results
        mock_total_calls_result = MagicMock()
        mock_total_calls_result.scalar.return_value = 100
        
        mock_booked_jobs_result = MagicMock()
        mock_booked_jobs_result.scalar.return_value = 30
        
        def mock_execute(query):
            if "total_calls_query" in str(query):
                result = MagicMock()
                result.scalar.return_value = 100
                return result
            elif "booked_jobs_query" in str(query):
                result = MagicMock()
                result.scalar.return_value = 30
                return result
            return MagicMock()
        
        mock_session.execute.side_effect = mock_execute
        
        metrics_repo = MetricsRepository(mock_session)
        
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        result = await metrics_repo.get_metrics_for_period(
            client_id="test-client",
            start_date=start_date,
            end_date=end_date,
        )
        
        assert result["total_calls"] == 100
        assert result["booked_jobs"] == 30
        assert result["revenue"] == 15000.0  # 30 * 500
        assert result["conversion_rate"] == 30.0  # (30/100) * 100
    
    @pytest.mark.asyncio
    async def test_get_call_volume_by_day(self):
        """Test get_call_volume_by_day method."""
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock query result
        mock_rows = [
            MagicMock(date=datetime(2026, 1, 27).date(), call_count=25),
            MagicMock(date=datetime(2026, 1, 26).date(), call_count=30),
            MagicMock(date=datetime(2026, 1, 25).date(), call_count=20),
        ]
        
        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        mock_session.execute.return_value = mock_result
        
        metrics_repo = MetricsRepository(mock_session)
        
        result = await metrics_repo.get_call_volume_by_day(
            client_id="test-client",
            days=7,
        )
        
        assert len(result) == 3
        assert result[0]["date"] == "2026-01-27"
        assert result[0]["call_count"] == 25
        assert result[1]["date"] == "2026-01-26"
        assert result[1]["call_count"] == 30
    
    @pytest.mark.asyncio
    async def test_get_revenue_by_service_type(self):
        """Test get_revenue_by_service_type method."""
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock query result
        mock_rows = [
            MagicMock(service_requested="plumbing", qualified_count=15),
            MagicMock(service_requested="hvac", qualified_count=10),
        ]
        
        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        mock_session.execute.return_value = mock_result
        
        metrics_repo = MetricsRepository(mock_session)
        
        result = await metrics_repo.get_revenue_by_service_type(
            client_id="test-client",
            period="30d",
        )
        
        assert len(result) == 2
        assert result[0]["service_type"] == "plumbing"
        assert result[0]["qualified_count"] == 15
        assert result[0]["revenue"] == 6750.0  # 15 * 450
        assert result[0]["avg_job_value"] == 450.0
    
    @pytest.mark.asyncio
    async def test_get_conversion_funnel(self):
        """Test get_conversion_funnel method."""
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock query results
        def mock_execute(query):
            result = MagicMock()
            if "total_calls_query" in str(query):
                result.scalar.return_value = 100
            elif "appointments_query" in str(query):
                result.scalar.return_value = 30
            elif "completed_jobs_query" in str(query):
                result.scalar.return_value = 25
            return result
        
        mock_session.execute.side_effect = mock_execute
        
        metrics_repo = MetricsRepository(mock_session)
        
        result = await metrics_repo.get_conversion_funnel(
            client_id="test-client",
            period="30d",
        )
        
        assert result["funnel"]["calls"] == 100
        assert result["funnel"]["answered"] == 100
        assert result["funnel"]["appointments"] == 30
        assert result["funnel"]["completed"] == 25
        assert result["rates"]["answer_rate"] == 100.0
        assert result["rates"]["appointment_rate"] == 30.0
        assert result["rates"]["completion_rate"] == 83.33
