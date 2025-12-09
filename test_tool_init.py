
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from agent_framework_azure_ai import AzureAIAgentClient
from agent_framework import MCPStreamableHTTPTool
from dotenv import load_dotenv, find_dotenv

print(f"Found .env at: {find_dotenv()}")
load_dotenv(override=True)

def test_tool_init():
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    print(f"Endpoint: {endpoint}")
    print(f"All AZURE env vars: {[k for k in os.environ if 'AZURE' in k]}")
    credential = DefaultAzureCredential()
    client = AzureAIAgentClient(project_endpoint=endpoint, credential=credential)
    
    print("Attempting to init tool with chat_client...")
    try:
        tool = MCPStreamableHTTPTool(
            name="test",
            url="http://test",
            chat_client=client
        )
        print("Success with chat_client!")
    except Exception as e:
        print(f"Failed with chat_client: {e}")

    print("\nAttempting to init tool with agents_client...")
    try:
        tool = MCPStreamableHTTPTool(
            name="test",
            url="http://test",
            agents_client=client
        )
        print("Success with agents_client!")
    except Exception as e:
        print(f"Failed with agents_client: {e}")

if __name__ == "__main__":
    test_tool_init()
