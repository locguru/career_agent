import os
import pickle
import json
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google import genai

# We only need read access to your inbox
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """Authenticates the user using your local credentials."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError("Please place your 'credentials.json' file in this directory.")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def fetch_recent_career_emails(service):
    """
    Natively streams complete conversational thread structures directly from the
    underlying Label_17 system node, preserving older recruiter context with recent replies.
    """
    # 🚀 TARGET SYSTEM NODE: Point the API directly at the immutable label ID mapping
    target_label_id = 'Label_17'
    print(f"📡 Requesting active conversation THREADS directly from system node: '{target_label_id}'...")
    
    # Fetch thread collections ordered natively by overall conversation activity date
    results = service.users().threads().list(
        userId='me',
        labelIds=[target_label_id],
        maxResults=50  # Keep lookback wide to absorb older threads safely
    ).execute()
    
    threads = results.get('threads', [])
    
    if not threads:
        print("🛑 No active conversation threads found inside your designated Career folder node.")
        return None

    print(f"📊 Identified {len(threads)} unique conversation pipelines. Extracting message arrays...")
    
    thread_payload = []
    for thread in threads:
        try:
            # Download the full conversational node tree (captures incoming text + outgoing sent replies)
            thread_detail = service.users().threads().get(userId='me', id=thread['id'], format='full').execute()
            msg_list = thread_detail.get('messages', [])
            
            thread_messages_text = []
            subject = "No Subject"
            
            for msg in msg_list:
                payload = msg.get('payload', {})
                headers = payload.get('headers', [])
                
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), subject)
                sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown Date')
                
                # Recursive parser to traverse multipart alternative mime-types safely
                def extract_body_text(parts_list):
                    for part in parts_list:
                        mime = part.get('mimeType', '')
                        if mime == 'text/plain' and 'data' in part.get('body', {}):
                            import base64
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
                    import base64
                    body_content = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
                    
                if not body_content.strip():
                    body_content = msg.get('snippet', '')
                    
                # Clean up excess whitespace formatting constraints and enforce window token sizes
                clean_body = " ".join(body_content.split())[:1200]
                thread_messages_text.append(f"From: {sender}\nDate: {date}\nContent: {clean_body}\n---")
            
            thread_payload.append({
                "thread_id": thread['id'],
                "subject": subject,
                "conversation_history": "\n".join(thread_messages_text)
            })
        except Exception:
            continue  # Quietly bypass any isolated rate hiccups
            
    return thread_payload

def analyze_and_draft_with_gemini(real_emails):
    """Uses a robust semantic prompt to let Gemini evaluate your real inbox items."""
    print("🧠 Performing a pure Semantic Intelligence Scan over your unfiltered data...")
    client = genai.Client()
    current_date = datetime.now().strftime("%B %d, %Y")

    robust_prompt = f"""
    You are the built-in Gemini Search Agent inside Gmail. Your task is to perform an advanced semantic evaluation over the unfiltered email thread dump provided below.
    
    Today's date is: {current_date}
    
    Raw Email Dataset:
    {real_emails}
    
    ---
    
    ### STEP 1: SEMANTIC SEARCH FILTERS
    Find all exchanges in my gmail and specifically from the Career label with recruiters from the last 24 months. In addition include all
    email threads from the last 24 months with emails ending with @google.com. Ignore emails from me (Itai Ram, itairam@gmail.com).
    
    ---
    
    ### STEP 2: DRAFT OUTPUT GENERATION
    List all results in a bulleted list with the email of the sender, date, and title. Since you are pulling from a list of threads some of which
    are part of the same email exchange, dedupe them so you have onlt one bullet per email exchange. 
      
    If zero threads match the semantic profile, explicitly state: 'No cold recruiter threads matching the criteria found.'
    """ 

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=robust_prompt,
    )
    return response.text

if __name__ == '__main__':
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ Error: Please set your GEMINI_API_KEY environment variable first.")
    else:
        try:
            gmail_service = get_gmail_service()
            real_inbox_data = fetch_recent_career_emails(gmail_service)
            
            if not real_inbox_data:
                print("🛑 No emails found matching the criteria folder parameters.")
            else:
                # Local JSON dump audit file
                with open("raw_gmail_dump.json", "w", encoding="utf-8") as f:
                    json.dump(real_inbox_data, f, indent=4, ensure_ascii=False)
                
                report = analyze_and_draft_with_gemini(real_inbox_data)
                print("\n" + "="*50)
                print("🚀 LIVE SEMANTIC AGENT REPORT")
                print("="*50)
                print(report)
        except Exception as e:
            print(f"\n❌ Execution Error: {str(e)}")