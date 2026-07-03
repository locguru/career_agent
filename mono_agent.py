import asyncio
import os
import json
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google import genai
from google.genai import types

load_dotenv()

# Initialize the Gemini Client (automatically picks up GEMINI_API_KEY from .env)
gemini_client = genai.Client()

async def main():
    # Configure the local MCP Filesystem Server
    server_params = StdioServerParameters(
        command="uvx",
        args=["mcp-server-filesystem", os.path.expanduser("~/Desktop")]
    )
    
    print("Connecting to MCP Server via stdio...")
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as mcp_session:
            await mcp_session.initialize()
            print("Connected to MCP successfully!")
            
            # 1. Discover tools from MCP Server
            mcp_response = await mcp_session.list_tools()
            print(f"\nDiscovered {len(mcp_response.tools)} MCP tools.")
            
            # 2. Convert MCP tools to Gemini Function Declarations
            gemini_tools = []
            for tool in mcp_response.tools:
                gemini_tools.append(
                    types.FunctionDeclaration(
                        name=tool.name,
                        description=tool.description,
                        parameters=tool.inputSchema, 
                    )
                )
            
            # Wrap them into Gemini's expected Tool structure
            tool_config = types.Tool(function_declarations=gemini_tools)
            
            # 3. Define prompt and call Gemini
            user_prompt = "Can you list the files on my Desktop?"
            print(f"\nUser: {user_prompt}")
            
            # We use gemini-2.5-flash as it's lightning fast and excellent at tool use
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    tools=[tool_config]
                )
            )
            
            # 4. Handle Tool/Function Calls
            if response.function_calls:
                for call in response.function_calls:
                    print(f"\n[Gemini requested tool]: '{call.name}'")
                    print(f"[Arguments]: {call.args}")
                    
                    # Execute the tool via the live MCP Session
                    mcp_result = await mcp_session.call_tool(call.name, arguments=call.args)
                    
                    # Extract text output from MCP response
                    tool_output = "".join([c.text for c in mcp_result.content if hasattr(c, 'text')])
                    print(f"[MCP Tool Output]:\n{tool_output}")
                    
                    # 5. Send the data back to Gemini to get a final conversational response
                    final_response = gemini_client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[
                            types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)]),
                            response.candidates[0].content, 
                            types.Content(
                                role="tool", 
                                parts=[
                                    types.Part.from_function_response(
                                        name=call.name,
                                        response={"result": tool_output}
                                    )
                                ]
                            )
                        ],
                        config=types.GenerateContentConfig(tools=[tool_config])
                    )
                    
                    print(f"\nFinal Agent Response:\n{final_response.text}")
            else:
                print(f"\nFinal Agent Response:\n{response.text}")

if __name__ == "__main__":
    asyncio.run(main())
