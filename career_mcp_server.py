import sys
import os
import json
import pickle
import base64
from googleapiclient.discovery import build
from datetime import datetime
import datetime as dt

def get_gmail_service():
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            return build('gmail', 'v1', credentials=pickle.load(token))
    raise FileNotFoundError("Missing token.pickle!")

def fetch_recent_career_emails(lookback_months=None):
    try:
        service = get_gmail_service()

        if lookback_months is None:
            return "Error: lookback_months parameter is required by this server."
            
        days_to_subtract = int(lookback_months) * 30
        start_date = dt.date.today() - dt.timedelta(days=days_to_subtract)
        search_query = f"after:{start_date:%Y/%m/%d}"     

        messages = []
        page_token = None

        while True:
            result = service.users().messages().list(
                userId="me",
                labelIds=["Label_17"],
                q=search_query,
                pageToken=page_token,
                maxResults=500
            ).execute()

            messages.extend(result.get("messages", []))
            print(f"Fetched {len(result.get('messages', []))} messages in this page", file=sys.stderr)

            page_token = result.get("nextPageToken")
            if not page_token:
                break

        print(f"Total messages fetched: {len(messages)}", file=sys.stderr)

        if not messages:
            return "No conversation threads found inside the designated Career folder node."

        unique_thread_ids = {msg['threadId'] for msg in messages}    
        print(f"Found {len(unique_thread_ids)} unique threads", file=sys.stderr)

        thread_payload = []
        for thread_id in unique_thread_ids:
            thread_detail = service.users().threads().get(userId='me', id=thread_id, format='full').execute()
            msg_list = thread_detail.get('messages', [])
            
            thread_messages_text = []
            subject = "No Subject"
            
            for msg in msg_list:
                payload = msg.get('payload', {})
                headers = payload.get('headers', [])
                
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), subject)
                sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown Date')

                def extract_body_text(parts_list):
                    for part in parts_list:
                        mime = part.get('mimeType', '')
                        if mime == 'text/plain' and 'data' in part.get('body', {}):
                            return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        if 'parts' in part:
                            nested_res = extract_body_text(part['parts'])
                            if nested_res:
                                return nested_res
                    return ""

                body_content = ""
                if 'parts' in payload:
                    body_content = extract_body_text(payload['parts'])
                elif 'data' in payload.get('body', {}):
                    body_content = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
                    
                if not body_content.strip():
                    body_content = msg.get('snippet', '')

                # --- TOKEN DE-BLOATER CRITICAL FIXES ---
                # 1. Strip out lines starting with '>' (traditional email thread replies)
                lines = body_content.splitlines()
                clean_lines = [line for line in lines if not line.strip().startswith('>')]
                body_content = "\n".join(clean_lines)

                # 2. Cap individual message length to prevent giant legal disclaimers/boilerplate from blowing the context
                if len(body_content) > 3000:
                    body_content = body_content[:3000] + "... [Truncated by Server]"
                
                clean_body = " ".join(body_content.split())
                thread_messages_text.append(f"From: {sender}\nDate: {date}\nContent: {clean_body}\n---")
            
            thread_payload.append(f"=== THREAD ID: {thread_id} ===\nSubject: {subject}\n" + "\n".join(thread_messages_text))
            
        return "\n\n=======================\n\n".join(thread_payload)
    except Exception as e:
        return f"Error: {str(e)}"

def serve():
    """A raw standard I/O loop processing incoming JSON-RPC communication."""
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if request.get("method") == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "tools": [{
                            "name": "fetch_recent_career_emails",
                            "description": "Scans custom folder Label_17 and returns recent conversational threads.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                     "lookback_months": {"type": "number", "description": "The number of months to look back from today."} 
                                },
                                "required": ["lookback_months"]    
                            }
                        }]
                    }
                }
            elif request.get("method") == "tools/call":
                args = request.get("params", {}).get("arguments", {})
                lookback_months = args.get("lookback_months")
                data_output = fetch_recent_career_emails(lookback_months=lookback_months)
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {"content": [{"type": "text", "text": data_output}]}
                }
            else:
                response = {"jsonrpc": "2.0", "id": request.get("id"), "error": {"message": "Unknown method"}}
            
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except Exception:
            continue

if __name__ == "__main__":
    serve()