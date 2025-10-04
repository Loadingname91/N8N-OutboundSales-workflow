Node Conversion Table

| n8n Node Name                          | n8n Node Type                      | Custom Req File | Functionality Translated                 | LangGraph Implementation | Dependencies               | Notes                                   |
|----------------------------------------|------------------------------------|-----------------|------------------------------------------|--------------------------|----------------------------|-----------------------------------------|
| When clicking ‘Execute workflow’       | manualTrigger                       | -               | Start execution manually                 | manual_trigger_node      | built-in                   | Initializes state                       |
| Google Sheets                          | googleSheets (read)                 | -               | Read company URLs from Sheet1 A:A        | load_company_urls        | google-api-python-client   | Reads and validates URLs                |
| HTTP Request                           | httpRequest                         | -               | Fetch website HTML                       | fetch_html               | httpx, tenacity            | Follow redirects, GET                  |
| HTML                                   | html                                | -               | Extract body text                        | extract_body_text        | beautifulsoup4             | CSS selector body                      |
| OpenAI - Summarizer                    | @n8n/n8n-nodes-langchain.openAi     | -               | Summarize website content                | summarize_company        | openai, tenacity           | GPT-4o-mini prompt                     |
| Hunter                                 | hunter                              | -               | Domain search for contacts               | hunter_lookup            | httpx, tenacity            | Uses Hunter API                        |
| If                                     | if                                  | -               | Check if emails exist                    | conditional has_emails   | built-in                   | Routes on email presence               |
| Google Sheets - Log Failed Lookups     | googleSheets (append)               | -               | Record failures in Failures sheet        | log_failures             | google-api-python-client   | Append domain and skip to next company |
| Edit Fields - Prepare Update Data      | set                                 | -               | Prepare success payload                  | prepare_success_node     | built-in                   | State reset marker                     |
| OpenAI - email body                    | @n8n/n8n-nodes-langchain.openAi     | -               | Generate cold email body                 | generate_email_body      | openai, tenacity           | Inject context and examples            |
| OpenAI - subject                       | @n8n/n8n-nodes-langchain.openAi     | -               | Generate subject line                    | generate_subject         | openai, tenacity           | 3–4 word subject                      |
| Gmail                                  | gmail                               | -               | Create draft with body/subject           | create_gmail_draft       | google-api-python-client   | Stores draft response                  |
| Google Sheets - Update Success Log     | googleSheets (append/update)        | -               | Update successes in Sheet1               | update_success_log       | google-api-python-client   | Append contact info                    |

Custom Node Implementation Details

None; workflow contains only standard n8n nodes, so no `/req-for-custom-nodes` integrations were required.

Dependencies
- langgraph>=0.0.40
- langchain-core>=0.1.38
- httpx>=0.27.0
- beautifulsoup4>=4.12.3
- openai>=1.14.0
- tenacity>=8.2.3
- google-api-python-client>=2.121.0
- google-auth>=2.29.0
- python-dotenv>=1.0.1 (optional for env loading)

Configuration Notes

- OPENAI_API_KEY: OpenAI account key for GPT-4-turbo.
- HUNTER_API_KEY: Hunter.io API key.
- GOOGLE_SHEET_ID: Spreadsheet ID for both read/write operations.
- GOOGLE_TOKEN_JSON: JSON string with OAuth2 tokens (must include Sheets and Gmail scopes).
- Adjust `sheet_range`, `failure_sheet_range`, and `success_sheet_range` if sheet structure differs.
- Ensure Gmail draft creation scope (`gmail.modify`) is granted to the OAuth credentials.

Testing Instructions

1. Install dependencies in a virtualenv (`pip install -r requirements.txt`).
2. Export required environment variables or place them in a `.env` file.
3. Run `python workflows/main.py` and observe logs for each processed URL.
4. Verify Gmail drafts appear in the connected account and Sheets entries update in both the success and failure tabs.
5. For dry runs without sending drafts, mock `GmailClient.create_draft` and the Google Sheets writer methods.