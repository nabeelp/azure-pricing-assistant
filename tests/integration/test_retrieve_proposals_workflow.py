"""Integration test for retrieving multiple proposals workflow."""

import pytest
from unittest.mock import MagicMock

from src.core.session import InMemorySessionStore
from src.core.models import SessionData, ProposalBundle


class TestRetrieveProposalsWorkflow:
    """Test workflow for retrieving multiple proposals."""

    def test_workflow_complete_proposal_generation_and_retrieval(self):
        """
        Test the complete workflow:
        1. Generate a proposal for session 1
        2. Generate a proposal for session 2
        3. Retrieve all proposals via /api/proposals
        4. Verify both proposals are returned
        """
        # Setup: Create session store with two sessions that have proposals
        session_store = InMemorySessionStore()
        
        # Session 1: Web application proposal
        proposal1 = ProposalBundle(
            bom_text="# Bill of Materials - Web App\n- Azure App Service: P1v2",
            pricing_text="# Pricing Estimate\nTotal Monthly: $100.00",
            proposal_text="# Proposal for Web Application\nYour web app solution..."
        )
        session1 = SessionData(
            thread=MagicMock(),
            history=[
                {"role": "user", "content": "I need a web application"},
                {"role": "assistant", "content": "What region?"},
                {"role": "user", "content": "East US"},
            ],
            turn_count=3,
            bom_items=[
                {
                    "serviceName": "Azure App Service",
                    "sku": "P1v2",
                    "quantity": 1,
                    "region": "East US",
                    "armRegionName": "eastus",
                    "hours_per_month": 730,
                }
            ],
            proposal=proposal1,
        )
        session_store.set("web_app_session", session1)
        
        # Session 2: Database workload proposal
        proposal2 = ProposalBundle(
            bom_text="# Bill of Materials - Database\n- Azure SQL Database: S3",
            pricing_text="# Pricing Estimate\nTotal Monthly: $200.00",
            proposal_text="# Proposal for Database Solution\nYour database solution..."
        )
        session2 = SessionData(
            thread=MagicMock(),
            history=[
                {"role": "user", "content": "I need a SQL database"},
                {"role": "assistant", "content": "What tier?"},
                {"role": "user", "content": "Standard S3 in West US"},
            ],
            turn_count=3,
            bom_items=[
                {
                    "serviceName": "Azure SQL Database",
                    "sku": "S3",
                    "quantity": 1,
                    "region": "West US",
                    "armRegionName": "westus",
                    "hours_per_month": 730,
                }
            ],
            proposal=proposal2,
        )
        session_store.set("database_session", session2)
        
        # Session 3: Active session without proposal (should not be included)
        session3 = SessionData(
            thread=MagicMock(),
            history=[
                {"role": "user", "content": "I need help with Azure costs"},
            ],
            turn_count=1,
            bom_items=[],
            proposal=None,  # No proposal yet
        )
        session_store.set("active_session", session3)
        
        # Action: Retrieve all proposals using the session store method
        sessions_with_proposals = session_store.get_all_with_proposals()
        
        # Verification: Ensure only sessions with proposals are returned
        assert len(sessions_with_proposals) == 2
        assert "web_app_session" in sessions_with_proposals
        assert "database_session" in sessions_with_proposals
        assert "active_session" not in sessions_with_proposals
        
        # Verification: Each session has the correct proposal
        web_proposal = sessions_with_proposals["web_app_session"].proposal
        assert web_proposal is not None
        assert "Web App" in web_proposal.bom_text
        assert "$100.00" in web_proposal.pricing_text
        assert "web app solution" in web_proposal.proposal_text.lower()
        
        db_proposal = sessions_with_proposals["database_session"].proposal
        assert db_proposal is not None
        assert "Database" in db_proposal.bom_text
        assert "$200.00" in db_proposal.pricing_text
        assert "database solution" in db_proposal.proposal_text.lower()

    def test_workflow_start_new_session_after_viewing_proposals(self):
        """
        Test workflow:
        1. View all proposals (2 exist)
        2. Start a new session
        3. Generate a new proposal
        4. Verify count increased to 3
        """
        session_store = InMemorySessionStore()
        
        # Setup: Two existing proposals
        for i in range(1, 3):
            proposal = ProposalBundle(
                bom_text=f"BOM {i}",
                pricing_text=f"Pricing {i}",
                proposal_text=f"Proposal {i}",
            )
            session = SessionData(
                thread=MagicMock(),
                history=[],
                turn_count=0,
                proposal=proposal,
            )
            session_store.set(f"session_{i}", session)
        
        # Verification: Initially 2 proposals
        initial_proposals = session_store.get_all_with_proposals()
        assert len(initial_proposals) == 2
        
        # Action: Add a new session with proposal
        proposal3 = ProposalBundle(
            bom_text="BOM 3",
            pricing_text="Pricing 3",
            proposal_text="Proposal 3",
        )
        session3 = SessionData(
            thread=MagicMock(),
            history=[],
            turn_count=0,
            proposal=proposal3,
        )
        session_store.set("session_3", session3)
        
        # Verification: Now 3 proposals
        updated_proposals = session_store.get_all_with_proposals()
        assert len(updated_proposals) == 3
        assert "session_1" in updated_proposals
        assert "session_2" in updated_proposals
        assert "session_3" in updated_proposals

    def test_workflow_empty_proposals_list(self):
        """
        Test workflow with no proposals:
        1. Query all proposals when none exist
        2. Verify empty list is returned (not an error)
        """
        session_store = InMemorySessionStore()
        
        # Setup: Sessions without proposals
        for i in range(1, 4):
            session = SessionData(
                thread=MagicMock(),
                history=[],
                turn_count=0,
                proposal=None,  # No proposals
            )
            session_store.set(f"session_{i}", session)
        
        # Action & Verification: Get all proposals returns empty
        proposals = session_store.get_all_with_proposals()
        assert proposals == {}
        assert len(proposals) == 0
