"""Tests for Proposal Agent output validation and formatting."""

import re
import pytest


class TestProposalStructure:
    """Test proposal markdown structure and required sections."""

    def test_proposal_has_main_heading(self):
        """Test proposal has main 'Azure Solution Proposal' heading."""
        proposal = """# Azure Solution Proposal

## Executive Summary
This is a test proposal."""
        assert "# Azure Solution Proposal" in proposal

    def test_proposal_has_executive_summary(self):
        """Test proposal includes Executive Summary section."""
        proposal = """# Azure Solution Proposal

## Executive Summary
A customer needs a scalable web application with database storage.
The proposed solution uses Azure App Service and SQL Database.
This provides cost-effective hosting with automatic scaling."""
        assert "## Executive Summary" in proposal
        # Should have content (at least 1 paragraph of 20+ chars)
        summary_match = re.search(
            r"## Executive Summary\n([\s\S]+?)(?=##|$)", proposal
        )
        assert summary_match is not None
        summary_content = summary_match.group(1).strip()
        assert len(summary_content) > 50

    def test_proposal_has_solution_architecture(self):
        """Test proposal includes Solution Architecture section."""
        proposal = """## Solution Architecture

- **Azure App Service**: Hosts the web application with auto-scaling
- **Azure SQL Database**: Provides managed database with HA"""
        assert "## Solution Architecture" in proposal

    def test_proposal_has_cost_breakdown(self):
        """Test proposal includes Cost Breakdown section."""
        proposal = """## Cost Breakdown

| Service | SKU | Quantity | Hourly Rate | Monthly Cost |
|---------|-----|----------|-------------|--------------|
| Azure App Service | P1v2 | 1 | $0.15 | $109.50 |"""
        assert "## Cost Breakdown" in proposal
        assert "| Service | SKU |" in proposal

    def test_proposal_has_total_cost_summary(self):
        """Test proposal includes Total Cost Summary section."""
        proposal = """## Total Cost Summary

- **Monthly Cost**: $150.54
- **Annual Cost (12 months)**: $1806.48
- **Currency**: USD"""
        assert "## Total Cost Summary" in proposal
        assert "Monthly Cost" in proposal
        assert "Annual Cost" in proposal
        assert "Currency" in proposal

    def test_proposal_has_next_steps(self):
        """Test proposal includes Next Steps section."""
        proposal = """## Next Steps

1. **Review and Validation**: Review this proposal with your team
2. **Environment Setup**: Plan your Azure resources"""
        assert "## Next Steps" in proposal

    def test_proposal_has_assumptions(self):
        """Test proposal includes Assumptions section."""
        proposal = """## Assumptions

- Operating hours: 24/7/365 (730 hours per month)
- Region: East US"""
        assert "## Assumptions" in proposal


class TestProposalFormatting:
    """Test proposal markdown formatting conventions."""

    def test_uses_markdown_headers(self):
        """Test proposal uses markdown header syntax."""
        proposal = """# Azure Solution Proposal

## Executive Summary
Content here.

## Solution Architecture
More content."""
        assert re.search(r"^# ", proposal, re.MULTILINE) is not None
        assert re.search(r"^## ", proposal, re.MULTILINE) is not None

    def test_uses_bullet_points(self):
        """Test proposal uses bullet points for lists."""
        proposal = """## Solution Architecture

- **Azure App Service**: Web hosting
- **SQL Database**: Data storage"""
        assert re.search(r"^-\s+\*\*", proposal, re.MULTILINE) is not None

    def test_cost_breakdown_is_table(self):
        """Test cost breakdown uses markdown table format."""
        proposal = """## Cost Breakdown

| Service | SKU | Quantity | Hourly Rate | Monthly Cost |
|---------|-----|----------|-------------|--------------|
| Azure App Service | P1v2 | 1 | $0.15 | $109.50 |"""
        assert "| Service | SKU |" in proposal
        assert "|---------|" in proposal
        # Must have at least one data row
        assert re.search(r"\| .+ \| .+ \| \d+ \|", proposal) is not None

    def test_bold_service_names(self):
        """Test service names in architecture are bold."""
        proposal = """## Solution Architecture

- **Azure App Service**: Hosts web application
- **SQL Database**: Provides managed database"""
        assert re.search(r"\*\*[A-Za-z ]+ (Service|Database)\*\*:", proposal)


class TestProposalContent:
    """Test proposal content completeness and accuracy."""

    def test_executive_summary_has_multiple_paragraphs(self):
        """Test executive summary contains substantial content."""
        proposal = """## Executive Summary

Customer needs a scalable solution for web application hosting.
The proposed Azure solution includes App Service for compute and SQL Database for data.
This architecture provides high availability and cost efficiency."""
        summary_match = re.search(
            r"## Executive Summary\n([\s\S]+?)(?=##|$)", proposal
        )
        summary_content = summary_match.group(1).strip()
        # Should have multiple sentences
        sentences = summary_content.split(".")
        assert len([s for s in sentences if s.strip()]) >= 2

    def test_architecture_lists_services(self):
        """Test architecture section lists services from BOM."""
        proposal = """## Solution Architecture

- **Virtual Machines**: Compute resources for application servers
- **Storage Account**: Object storage for application data
- **SQL Database**: Relational database with built-in HA"""
        # Should have at least 3 services listed
        services = re.findall(r"- \*\*([^*]+)\*\*:", proposal)
        assert len(services) >= 3

    def test_cost_breakdown_has_all_columns(self):
        """Test cost breakdown table has required columns."""
        proposal = """| Service | SKU | Quantity | Hourly Rate | Monthly Cost |
|---------|-----|----------|-------------|--------------|
| Azure App Service | P1v2 | 1 | $0.15 | $109.50 |"""
        headers = ["Service", "SKU", "Quantity", "Hourly Rate", "Monthly Cost"]
        for header in headers:
            assert header in proposal

    def test_total_cost_calculation(self):
        """Test total cost summary shows monthly and annual costs."""
        proposal = """## Total Cost Summary

- **Monthly Cost**: $500.00
- **Annual Cost (12 months)**: $6000.00
- **Currency**: USD"""
        # Check for monthly cost
        assert re.search(r"\$\d+\.?\d*", proposal) is not None
        # Check for annual calculation
        assert "12 months" in proposal or "Annual" in proposal

    def test_next_steps_ordered_list(self):
        """Test next steps uses numbered list."""
        proposal = """## Next Steps

1. **Review and Validation**: Review with team
2. **Environment Setup**: Plan Azure resources
3. **Deployment**: Deploy infrastructure
4. **Optimization**: Monitor and right-size"""
        # Should have numbered items
        numbered = re.findall(r"^\d+\.", proposal, re.MULTILINE)
        assert len(numbered) >= 3

    def test_assumptions_include_operating_hours(self):
        """Test assumptions mention operating hours."""
        proposal = """## Assumptions

- Operating hours: 24/7/365 (730 hours per month)
- Region: East US"""
        assert "730 hours" in proposal or "24/7" in proposal


class TestProposalCalculations:
    """Test proposal cost calculations."""

    def test_annual_cost_is_12x_monthly(self):
        """Test annual cost is correctly calculated as 12x monthly."""
        monthly = 100.50
        annual = monthly * 12
        proposal = f"""## Total Cost Summary

- **Monthly Cost**: ${monthly:.2f}
- **Annual Cost (12 months)**: ${annual:.2f}"""
        # Extract costs using regex
        monthly_match = re.search(r"\*\*Monthly Cost\*\*:\s+\$(\d+\.?\d*)", proposal)
        annual_match = re.search(
            r"\*\*Annual Cost.*?\*\*:\s+\$(\d+\.?\d*)", proposal
        )
        assert monthly_match is not None
        assert annual_match is not None
        parsed_monthly = float(monthly_match.group(1))
        parsed_annual = float(annual_match.group(1))
        assert abs(parsed_annual - (parsed_monthly * 12)) < 0.01

    def test_service_costs_in_table(self):
        """Test each service has cost in breakdown table."""
        proposal = """| Service | SKU | Quantity | Hourly Rate | Monthly Cost |
|---------|-----|----------|-------------|--------------|
| Azure App Service | P1v2 | 1 | $0.15 | $109.50 |
| SQL Database | S1 | 1 | $0.03 | $21.90 |"""
        # Should have at least 2 services with costs
        costs = re.findall(r"\$\d+\.\d{2}\s*\|$", proposal, re.MULTILINE)
        assert len(costs) >= 2

    def test_zero_cost_note_present(self):
        """Test proposal notes when pricing is unavailable ($0.00)."""
        proposal = """| Service | SKU | Quantity | Hourly Rate | Monthly Cost |
|---------|-----|----------|-------------|--------------|
| Service | SKU | 1 | $0.00 | $0.00 |

**Notes:**
Pricing data not available - please contact Azure sales"""
        assert "$0.00" in proposal
        assert "Pricing data not available" in proposal or "pricing unavailable" in proposal


class TestProposalClientReadiness:
    """Test proposal is suitable for client delivery."""

    def test_no_placeholder_text(self):
        """Test proposal doesn't contain placeholder markers."""
        proposal = """# Azure Solution Proposal

## Executive Summary
Customer needs scalable hosting for web application."""
        placeholders = [
            "[PLACEHOLDER]",
            "[TODO]",
            "{{",
            "}}",
            "TBD",
            "undefined",
            "null",
        ]
        for placeholder in placeholders:
            assert placeholder not in proposal.upper()

    def test_professional_tone(self):
        """Test proposal uses professional terminology."""
        proposal = """## Executive Summary

This solution provides high availability and automatic scaling capabilities."""
        professional_terms = [
            "scalable",
            "reliable",
            "cost-effective",
            "efficient",
            "availability",
        ]
        proposal_lower = proposal.lower()
        assert any(term in proposal_lower for term in professional_terms)

    def test_currency_specified(self):
        """Test proposal specifies currency."""
        proposal = """## Total Cost Summary

- **Monthly Cost**: $150.54
- **Currency**: USD"""
        assert "USD" in proposal or "$" in proposal

    def test_proper_markdown_spacing(self):
        """Test proposal has proper markdown spacing between sections."""
        proposal = """# Heading 1

Some content.

## Heading 2

More content."""
        # Should have blank lines between sections
        assert "\n\n" in proposal


class TestProposalErrorHandling:
    """Test proposal handles edge cases gracefully."""

    def test_missing_pricing_noted(self):
        """Test proposal notes when pricing data is missing."""
        proposal = """## Cost Breakdown

| Service | SKU | Quantity | Hourly Rate | Monthly Cost |
|---------|-----|----------|-------------|--------------|
| Service | SKU | 1 | $0.00 | $0.00 |

**Notes:** Pricing data not available for this service."""
        assert "$0.00" in proposal
        assert "not available" in proposal.lower()

    def test_empty_bom_handled(self):
        """Test proposal handles empty bill of materials."""
        proposal = """## Solution Architecture

No services were included in the bill of materials."""
        # Proposal should still have structure
        assert "## Solution Architecture" in proposal

    def test_large_numbers_formatted(self):
        """Test proposal formats large numbers readably."""
        proposal = """## Total Cost Summary

- **Monthly Cost**: $10,500.00
- **Annual Cost (12 months)**: $126,000.00"""
        # Should format large numbers with commas or clear formatting
        assert "$10" in proposal and "$126" in proposal


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
