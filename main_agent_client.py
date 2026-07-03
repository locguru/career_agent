import os
import sys
import json
import subprocess
from google import genai
from google.genai import types


def run_pure_mcp_agent():
    LOOKBACK_WINDOW_MONTHS = 12
    # Initialize the modern native Google GenAI SDK Client
    client = genai.Client()

    print("🚀 Spawning local career_mcp_server.py background subprocess via Standard I/O...")
    server_process = subprocess.Popen(
        [sys.executable, "career_mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True
    )

    # 1. HANDSHAKE / DISCOVERY
    discovery_request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    server_process.stdin.write(json.dumps(discovery_request) + "\n")
    server_process.stdin.flush()

    raw_response = server_process.stdout.readline()
    discovered_data = json.loads(raw_response)
    tool_manifest = discovered_data["result"]["tools"][0]
    print(f"✅ Protocol handshaking complete. Discovered tool: '{tool_manifest['name']}'")

    # 2. PROMPT ORCHESTRATION WITH GEMINI
    system_instruction = (
        f"You are an executive career tracking system. Summarize all the exchanges I have had with recruiters from the past {LOOKBACK_WINDOW_MONTHS} months."
    )

    user_prompt = f"""
    First, use the available tool to pull the raw career email threads.
    Once you receive the data back from the tool, apply the following filters to the text data to create your final report:

    ### SEMANTIC SEARCH FILTERS (Apply AFTER fetching data)
    Find all exchanges from the Career label with recruiters from the last {LOOKBACK_WINDOW_MONTHS} months.
    In addition, include all email threads from the last {LOOKBACK_WINDOW_MONTHS} months with emails ending with @google.com.
    ...
    """

    # Map the tool discovery parameters into Gemini structure schemas
    gemini_tools = [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name=tool_manifest["name"],
                    description="REQUIRED FIRST STEP. Call this tool immediately to fetch all raw email conversation history threads for the model to analyze.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                             "lookback_months": types.Schema(
                                type="NUMBER",
                                description=f"Number of months to look back. Set this to exactly {LOOKBACK_WINDOW_MONTHS}."
                             )
                        }
                    )
                )
            ]
        )
    ]

    print("🤖 Prompting Gemini (2.5 Flash) with tool manifest schemas...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=gemini_tools,
            temperature=0.3
        )
    )

    # 3. TOOL EXECUTION LOOP
    if response.function_calls:
        call_intent = response.function_calls[0]
        print(f"🎯 Gemini requested tool invocation: '{call_intent.name}'")

        function_args = dict(call_intent.args)
        function_args["lookback_months"] = int(LOOKBACK_WINDOW_MONTHS)

        execution_command = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": call_intent.name, "arguments": function_args}
        }

        server_process.stdin.write(json.dumps(execution_command) + "\n")
        server_process.stdin.flush()

        raw_execution_result = server_process.stdout.readline()
        execution_payload = json.loads(raw_execution_result)
        extracted_email_data = execution_payload["result"]["content"][0]["text"]
        print("📝 Email content streams pulled from server subprocess. Finalizing report...")

        # 🛠️ DEBUG ADDITION: Dump raw email data to a temporary inspection file
        try:
            debug_filepath = os.path.join(os.getcwd(), "mcp_debug_raw_emails.txt")
            with open(debug_filepath, "w", encoding="utf-8") as debug_file:
                debug_file.write(extracted_email_data)
            print(f"📁 [DEBUG] Successfully wrote raw data to: {debug_filepath}")
        except Exception as debug_err:
            print(f"⚠️ [DEBUG] Failed to write debug log file: {str(debug_err)}")

        generation_prompt = f"""
        Here is the raw data returned by your tool call execution.
        Please process it according to the original semantic filtering and deduplication rules:

        {user_prompt}

        ---
        RAW BACKEND TOOL PAYLOAD DATA FROM INBOX:
        {extracted_email_data}
        """

        final_report = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=generation_prompt,
            config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.3)
        )

        print("\n📊 FINAL MCP-ORCHESTRATED AGENT REPORT:\n")
        print(final_report.text)

    else:
        print("\n📊 FINAL REPORT (No tool call made):\n")
        print(response.text)

    server_process.terminate()


if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ Error: Please set your GEMINI_API_KEY environment variable first.")
        print("   export GEMINI_API_KEY=your_key_here")
    else:
        run_pure_mcp_agent()