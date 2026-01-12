"""Tests for streamlined Question Agent focusing on pricing essentials."""

import pytest
from src.agents.question_agent import create_question_agent


class TestStreamlinedInstructions:
    """Test that Question Agent instructions focus on pricing essentials."""

    def test_instructions_prioritize_pricing_essentials(self):
        """Instructions should explicitly list essential pricing information."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        # Check for essential information list
        assert "ESSENTIAL INFORMATION" in source or "prioritize" in source.lower()
        
        # Should mention key pricing factors
        assert "workload" in source.lower()
        assert "region" in source.lower()
        assert "service" in source.lower()
        assert "tier" in source.lower() or "sku" in source.lower()
        assert "quantity" in source.lower()

    def test_instructions_mention_efficiency_target(self):
        """Instructions should mention targeting 5-8 questions."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        # Should mention targeting fewer questions
        assert "5-8" in source or "efficient" in source.lower()

    def test_instructions_skip_non_essential_topics(self):
        """Instructions should explicitly skip architecture details not affecting pricing."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        # Should have guidance on what to skip
        assert "skip" in source.lower() or "not essential" in source.lower()

    def test_instructions_still_use_completion_format(self):
        """Instructions must preserve JSON completion format for orchestrator."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        # Must include completion criteria
        assert '```json' in source
        assert '"requirements"' in source
        assert '"done": true' in source

    def test_instructions_focus_on_region_early(self):
        """Instructions should prioritize asking about region early."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        # Region should be mentioned early in sequence
        assert "region" in source.lower()
        # Check it's in priority list or early sequence
        assert ("target azure region" in source.lower() or 
                "ask for target azure region early" in source.lower())

    def test_instructions_prioritize_service_selection(self):
        """Instructions should focus on service selection."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        # Should guide on service selection
        assert "service" in source.lower()
        assert ("which specific services" in source.lower() or 
                "azure services needed" in source.lower())

    def test_instructions_ask_about_service_tiers(self):
        """Instructions should include asking about service tiers/SKUs."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        # Should mention tiers or SKUs
        assert ("tier" in source.lower() or "sku" in source.lower())
        assert ("basic" in source.lower() and "standard" in source.lower() and 
                "premium" in source.lower())

    def test_instructions_ask_about_quantity(self):
        """Instructions should include asking about quantity/instances."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        assert "quantity" in source.lower()
        assert "instances" in source.lower() or "units" in source.lower()


class TestArchitectureQuestionsRemoved:
    """Test that non-essential architecture questions are removed or deprioritized."""

    def test_instructions_skip_deep_architecture_patterns(self):
        """Instructions should skip asking about architecture patterns not affecting pricing."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        # Should have SKIP section or similar guidance
        skip_section_exists = (
            "skip" in source.lower() and 
            ("architecture" in source.lower() or "pattern" in source.lower())
        )
        
        assert skip_section_exists

    def test_instructions_skip_networking_unless_affects_service(self):
        """Networking details should be skipped unless they affect service selection."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        # Should mention skipping networking or only asking if affects service
        if "networking" in source.lower():
            # If networking is mentioned, it should be in skip context
            assert ("skip" in source.lower() or 
                    "unless" in source.lower())

    def test_instructions_skip_security_features_unless_billable(self):
        """Security features should be skipped unless they're separate services."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        # Should mention skipping security features
        if "security" in source.lower() or "waf" in source.lower():
            assert ("skip" in source.lower() or 
                    "unless" in source.lower())


class TestCompletionEfficiency:
    """Test that completion criteria are streamlined."""

    def test_completion_criteria_includes_minimum_fields(self):
        """Completion criteria should list minimum required fields."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        # Should have completion criteria section
        assert "completion criteria" in source.lower() or "gather at minimum" in source.lower()
        
        # Should list essential fields
        completion_section = source[source.lower().find("completion"):] if "completion" in source.lower() else source
        
        assert "workload" in completion_section.lower()
        assert "region" in completion_section.lower()
        assert "service" in completion_section.lower()

    def test_completion_not_requiring_architecture_details(self):
        """Completion criteria should not require architecture component details."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        # Find completion criteria section
        if "completion criteria" in source.lower():
            completion_start = source.lower().find("completion criteria")
            completion_end = source.find("REQUIREMENTS SUMMARY", completion_start)
            if completion_end == -1:
                completion_end = source.find("FINAL RESPONSE", completion_start)
            
            completion_section = source[completion_start:completion_end]
            
            # Should NOT require these in completion criteria
            assert "architecture components" not in completion_section.lower()
            assert "vnet" not in completion_section.lower()
            assert "application gateway" not in completion_section.lower()

    def test_completion_does_not_require_availability_details(self):
        """Completion should not require high availability or redundancy details."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        # Find completion criteria
        if "completion criteria" in source.lower():
            completion_start = source.lower().find("completion criteria")
            completion_end = source.find("REQUIREMENTS SUMMARY", completion_start)
            if completion_end == -1:
                completion_end = len(source)
            
            completion_section = source[completion_start:completion_end]
            
            # Should NOT require redundancy/availability
            assert "redundancy" not in completion_section.lower()
            assert "high availability" not in completion_section.lower()
            assert "disaster recovery" not in completion_section.lower()


class TestQuestionSequence:
    """Test that question sequence is streamlined."""

    def test_sequence_starts_with_workload(self):
        """Question sequence should start with workload type."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        # Should have sequence guidance
        if "sequence" in source.lower():
            sequence_section = source[source.lower().find("sequence"):]
            
            # First question should be workload
            first_question = sequence_section[:500]  # Check first 500 chars of sequence
            assert "workload" in first_question.lower()

    def test_sequence_asks_region_early(self):
        """Region should be asked early in sequence (within first few questions)."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        # Should mention asking region early
        assert "region early" in source.lower() or "ask for target azure region" in source.lower()

    def test_sequence_includes_service_tier_question(self):
        """Sequence should include asking about service tier/SKU."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        if "sequence" in source.lower():
            sequence_section = source[source.lower().find("sequence"):]
            
            # Should ask about tier/SKU
            assert ("tier" in sequence_section.lower() or 
                    "sku" in sequence_section.lower())

    def test_sequence_does_not_include_environment_type(self):
        """Streamlined sequence should not ask about dev/qa/prod environment."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        if "sequence" in source.lower():
            sequence_section = source[source.lower().find("sequence"):]
            
            # Should NOT ask about environment type (not essential for pricing)
            assert "environment type" not in sequence_section.lower()
            assert "development/testing" not in sequence_section.lower()


class TestToolUsageGuidance:
    """Test that microsoft_docs_search tool usage is still available but focused."""

    def test_instructions_include_docs_search_tool(self):
        """Instructions should still mention microsoft_docs_search tool."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        assert "microsoft_docs_search" in source.lower()

    def test_docs_search_used_for_service_suggestions(self):
        """Tool should be used to suggest services, not architecture patterns."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        # Should mention using tool for service suggestions
        if "microsoft_docs_search" in source.lower():
            tool_section = source[source.lower().find("microsoft_docs_search"):][:1000]
            
            assert "service" in tool_section.lower()

    def test_docs_search_not_for_architecture_patterns(self):
        """Tool usage should not emphasize looking up architecture patterns."""
        from src.agents import question_agent
        import inspect
        
        source = inspect.getsource(question_agent.create_question_agent)
        
        # Should NOT have extensive architecture lookup guidance
        assert "reference architecture" not in source.lower() or "skip" in source.lower()
        assert "architecture-based questioning" not in source.lower()


class TestAgentCreation:
    """Test that agent creation still works correctly."""

    def test_create_question_agent_returns_chat_agent(self):
        """create_question_agent should return a ChatAgent instance."""
        from unittest.mock import Mock
        from agent_framework import ChatAgent
        
        mock_client = Mock()
        agent = create_question_agent(mock_client)
        
        assert isinstance(agent, ChatAgent)

    def test_agent_name_is_question_agent(self):
        """Agent name should be 'question_agent'."""
        from unittest.mock import Mock
        
        mock_client = Mock()
        agent = create_question_agent(mock_client)
        
        assert agent.name == "question_agent"
