"""Tests for delivery recovery job."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.workers.recovery_job import (
    DeliveryRecoveryJob, get_recovery_job,
    recovery_job_task, run_recovery_job_now
)
from app.core.enums import DeliveryChannel, DeliveryPurpose, DeliveryStatus


class TestDeliveryRecoveryJob:
    """Test delivery recovery job functionality."""
    
    @pytest.fixture
    def recovery_job(self):
        """Create recovery job instance."""
        return DeliveryRecoveryJob("redis://localhost:6379")
    
    @pytest.mark.asyncio
    async def test_find_stuck_deliveries(self, recovery_job):
        """Test finding stuck deliveries."""
        mock_delivery_records = [
            MagicMock(
                id="delivery-1",
                lead_id="lead-1",
                channel=DeliveryChannel.WEBHOOK,
                purpose=DeliveryPurpose.LEAD_DELIVERY,
                status=DeliveryStatus.PENDING,
                created_at=datetime.utcnow() - timedelta(minutes=10),
            ),
            MagicMock(
                id="delivery-2",
                lead_id="lead-2",
                channel=DeliveryChannel.SMS,
                purpose=DeliveryPurpose.FOLLOWUP_REMINDER,
                status=DeliveryStatus.PENDING,
                created_at=datetime.utcnow() - timedelta(minutes=8),
            ),
        ]
        
        with patch('app.workers.recovery_job.get_async_session_context') as mock_context:
            mock_session = AsyncMock()
            mock_delivery_repo = AsyncMock()
            mock_delivery_repo.get_stuck_pending_deliveries.return_value = mock_delivery_records
            
            mock_session.__aenter__.return_value = mock_session
            mock_context.return_value = mock_session
            
            with patch('app.workers.recovery_job.DeliveryRepository', return_value=mock_delivery_repo):
                stuck_deliveries = await recovery_job.find_stuck_deliveries()
                
                assert len(stuck_deliveries) == 2
                assert stuck_deliveries[0].id == "delivery-1"
                assert stuck_deliveries[1].id == "delivery-2"
                
                # Verify threshold calculation
                threshold_time = datetime.utcnow() - timedelta(minutes=5)
                mock_delivery_repo.get_stuck_pending_deliveries.assert_called_once_with(
                    threshold_time=threshold_time
                )
    
    @pytest.mark.asyncio
    async def test_find_stuck_deliveries_empty(self, recovery_job):
        """Test finding no stuck deliveries."""
        with patch('app.workers.recovery_job.get_async_session_context') as mock_context:
            mock_session = AsyncMock()
            mock_delivery_repo = AsyncMock()
            mock_delivery_repo.get_stuck_pending_deliveries.return_value = []
            
            mock_session.__aenter__.return_value = mock_session
            mock_context.return_value = mock_session
            
            with patch('app.workers.recovery_job.DeliveryRepository', return_value=mock_delivery_repo):
                stuck_deliveries = await recovery_job.find_stuck_deliveries()
                
                assert len(stuck_deliveries) == 0
    
    @pytest.mark.asyncio
    async def test_recover_delivery_success(self, recovery_job):
        """Test successful delivery recovery."""
        mock_delivery_record = MagicMock(
            id="delivery-1",
            lead_id="lead-1",
            channel=DeliveryChannel.WEBHOOK,
            purpose=DeliveryPurpose.LEAD_DELIVERY,
        )
        
        with patch('app.workers.recovery_job.enqueue_delivery_task') as mock_enqueue:
            with patch('app.workers.recovery_job.get_async_session_context') as mock_context:
                mock_session = AsyncMock()
                mock_audit_repo = AsyncMock()
                
                mock_session.__aenter__.return_value = mock_session
                mock_context.return_value = mock_session
                
                with patch('app.workers.recovery_job.AuditRepository', return_value=mock_audit_repo):
                    result = await recovery_job.recover_delivery(mock_delivery_record)
                    
                    assert result is True
                    mock_enqueue.assert_called_once_with("delivery-1")
                    mock_audit_repo.create_audit_log.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_recover_delivery_failure(self, recovery_job):
        """Test failed delivery recovery."""
        mock_delivery_record = MagicMock(
            id="delivery-1",
            lead_id="lead-1",
            channel=DeliveryChannel.WEBHOOK,
            purpose=DeliveryPurpose.LEAD_DELIVERY,
        )
        
        with patch('app.workers.recovery_job.enqueue_delivery_task') as mock_enqueue:
            mock_enqueue.side_effect = Exception("Queue error")
            
            with patch('app.workers.recovery_job.get_async_session_context') as mock_context:
                mock_session = AsyncMock()
                mock_audit_repo = AsyncMock()
                
                mock_session.__aenter__.return_value = mock_session
                mock_context.return_value = mock_session
                
                with patch('app.workers.recovery_job.AuditRepository', return_value=mock_audit_repo):
                    result = await recovery_job.recover_delivery(mock_delivery_record)
                    
                    assert result is False
    
    @pytest.mark.asyncio
    async def test_run_recovery_job_success(self, recovery_job):
        """Test complete recovery job with stuck deliveries."""
        mock_stuck_deliveries = [
            MagicMock(id="delivery-1", lead_id="lead-1"),
            MagicMock(id="delivery-2", lead_id="lead-2"),
            MagicMock(id="delivery-3", lead_id="lead-3"),
        ]
        
        # Mock find_stuck_deliveries to return stuck deliveries
        recovery_job.find_stuck_deliveries = AsyncMock(return_value=mock_stuck_deliveries)
        
        # Mock recover_delivery to succeed for first 2, fail for 3rd
        async def mock_recover(delivery):
            return delivery.id != "delivery-3"
        
        recovery_job.recover_delivery = mock_recover
        
        result = await recovery_job.run_recovery_job()
        
        assert result["total_stuck"] == 3
        assert result["recovered"] == 2
        assert result["failed"] == 1
    
    @pytest.mark.asyncio
    async def test_run_recovery_job_no_stuck(self, recovery_job):
        """Test recovery job with no stuck deliveries."""
        recovery_job.find_stuck_deliveries = AsyncMock(return_value=[])
        
        result = await recovery_job.run_recovery_job()
        
        assert result["total_stuck"] == 0
        assert result["recovered"] == 0
        assert result["failed"] == 0
    
    @pytest.mark.asyncio
    async def test_run_recovery_job_exception(self, recovery_job):
        """Test recovery job with exception."""
        recovery_job.find_stuck_deliveries = AsyncMock(side_effect=Exception("Database error"))
        
        result = await recovery_job.run_recovery_job()
        
        assert result["total_stuck"] == 0
        assert result["recovered"] == 0
        assert result["failed"] == 0
        assert "error" in result
    
    def test_get_recovery_job_singleton(self):
        """Test recovery job singleton pattern."""
        with patch('app.workers.recovery_job.settings') as mock_settings:
            mock_settings.redis_url = "redis://localhost:6379"
            
            job1 = get_recovery_job()
            job2 = get_recovery_job()
            
            assert job1 is job2
            assert job1.redis_url == "redis://localhost:6379"
    
    def test_recovery_job_task_sync_wrapper(self):
        """Test sync wrapper for async recovery job."""
        mock_stats = {
            "total_stuck": 2,
            "recovered": 1,
            "failed": 1,
        }
        
        with patch('app.workers.recovery_job.get_recovery_job') as mock_get_job:
            mock_job = AsyncMock()
            mock_job.run_recovery_job.return_value = mock_stats
            mock_get_job.return_value = mock_job
            
            result = recovery_job_task()
            
            assert result == mock_stats
            mock_job.run_recovery_job.assert_called_once()
    
    def test_run_recovery_job_now(self):
        """Test immediate execution of recovery job."""
        mock_stats = {
            "total_stuck": 1,
            "recovered": 1,
            "failed": 0,
        }
        
        with patch('app.workers.recovery_job.recovery_job_task', return_value=mock_stats):
            result = run_recovery_job_now()
            
            assert result == mock_stats


class TestRecoveryJobIntegration:
    """Integration tests for recovery job."""
    
    @pytest.mark.asyncio
    async def test_full_recovery_flow(self):
        """Test complete recovery flow with realistic data."""
        recovery_job = DeliveryRecoveryJob("redis://localhost:6379")
        
        # Create realistic stuck delivery records
        stuck_deliveries = [
            MagicMock(
                id="delivery-1",
                lead_id="lead-1",
                channel=DeliveryChannel.WEBHOOK,
                purpose=DeliveryPurpose.LEAD_DELIVERY,
                created_at=datetime.utcnow() - timedelta(minutes=10),
            ),
            MagicMock(
                id="delivery-2",
                lead_id="lead-2",
                channel=DeliveryChannel.SMS,
                purpose=DeliveryPurpose.FOLLOWUP_REMINDER,
                created_at=datetime.utcnow() - timedelta(minutes=8),
            ),
        ]
        
        # Mock the entire flow
        with patch('app.workers.recovery_job.get_async_session_context') as mock_context:
            mock_session = AsyncMock()
            mock_delivery_repo = AsyncMock()
            mock_audit_repo = AsyncMock()
            
            mock_session.__aenter__.return_value = mock_session
            mock_context.return_value = mock_session
            
            # Mock finding stuck deliveries
            mock_delivery_repo.get_stuck_pending_deliveries.return_value = stuck_deliveries
            
            with patch('app.workers.recovery_job.DeliveryRepository', return_value=mock_delivery_repo):
                with patch('app.workers.recovery_job.AuditRepository', return_value=mock_audit_repo):
                    with patch('app.workers.recovery_job.enqueue_delivery_task') as mock_enqueue:
                        # Run the job
                        result = await recovery_job.run_recovery_job()
                        
                        # Verify results
                        assert result["total_stuck"] == 2
                        assert result["recovered"] == 2
                        assert result["failed"] == 0
                        
                        # Verify deliveries were re-queued
                        assert mock_enqueue.call_count == 2
                        mock_enqueue.assert_any_call("delivery-1")
                        mock_enqueue.assert_any_call("delivery-2")
                        
                        # Verify audit logs were created
                        assert mock_audit_repo.create_audit_log.call_count == 2
