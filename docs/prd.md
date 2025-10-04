n8n Workflow Technical Specification
Global Workflow Summary
Objective: Automated outbound sales email campaign that scrapes company websites, finds contact information, generates personalized emails using AI, and sends them via Gmail while tracking successes and failures in Google Sheets.
Workflow Settings:

Execution Order: v1
Active Status: Disabled (active: false)
No global error workflow configured
No timezone settings specified
Standard execution without save progress enabled

Triggers:

Manual trigger only ("When clicking 'Execute workflow'")
No webhooks or scheduled triggers configured
Response timing: N/A (manual trigger)

Execution Rules:

No explicit concurrency limits defined
Sequential processing (one item at a time through the pipeline)
No global retry strategy configured
No timeout settings specified

Security:

No inbound authentication (manual trigger)
Outbound authentication via OAuth2 for Gmail and Google Sheets
API key authentication for Hunter.io and OpenAI services

Error Handling:

No global error handler configured
Individual node failures handled by conditional routing (If node)

Per Node Specification
1. When clicking 'Execute workflow'
Functionality: Manual workflow trigger that starts execution when user clicks the execute button in n8n interface.
Built-in Parameters to Replicate:

Trigger type: Manual activation
No authentication required
Single execution per click

Workflow-Specific Configuration:

None

Data Mapping:

Outputs empty initial data object

Success Path: → Google Sheets (read company URLs)
Error Path: Workflow stops if trigger fails

2. Google Sheets
Functionality: Reads company URLs from a Google Sheets spreadsheet, specifically from column A starting at row 1.
Built-in Parameters to Replicate:

Operation mode: Read
Authentication: OAuth2
Data location mode: Specify range A1 notation
Output format: JSON array

Workflow-Specific Configuration:

Spreadsheet: "Automated outbound sales"
Sheet: "Sheet1"
Range: Column A from row 1 to end (A1:A)
Expected data: List of company URLs

Data Mapping:

Outputs array of objects with companyUrl field

Success Path: → HTTP Request
Error Path: Workflow stops on authentication or read failure

3. HTTP Request
Functionality: Fetches the HTML content of each company website.
Built-in Parameters to Replicate:

Method: GET
Response format: File/binary data
Follow redirects: Enabled
Error handling: Default (stop on error)

Workflow-Specific Configuration:

URL: The company URL from the previous Google Sheets node
No additional headers or authentication

Data Mapping:

Input: companyUrl from Google Sheets
Output: Raw HTML content as binary data

Success Path: → HTML
Error Path: Workflow stops on HTTP error

4. HTML
Functionality: Extracts text content from the HTML body element using CSS selector.
Built-in Parameters to Replicate:

Operation: Extract HTML content
Extraction method: CSS selector
Output format: Text content

Workflow-Specific Configuration:

CSS Selector: "body"
Extract key name: "textContent"
Source data: Binary HTML from HTTP Request

Data Mapping:

Input: Raw HTML
Output: Object with textContent field containing extracted text

Success Path: → OpenAI- Summarizer
Error Path: Workflow stops on extraction failure

5. OpenAI- Summarizer
Functionality: Uses gpt-4o-mini to generate a concise summary of the company based on website content.
Built-in Parameters to Replicate:

Model selection: gpt-4o-mini
Message format: Single user message
Authentication: API key
Temperature/options: Default settings

Workflow-Specific Configuration:

Prompt: "Summarize the following website content. Focus on what the company does and its main value proposition. Keep it concise, under 75 words. Here is the content: [website text content]"

Data Mapping:

Input: textContent from HTML node
Output: AI-generated summary in message.content

Success Path: → Hunter
Error Path: Workflow stops on API error

6. Hunter
Functionality: Finds email addresses and contact information for a company domain using Hunter.io API.
Built-in Parameters to Replicate:

API endpoint: Domain search
Authentication: API key
Return format: JSON with email array
Filter: All positions (not only emails)

Workflow-Specific Configuration:

Domain extraction: Parse domain from company URL (remove protocol and path)
Search all available contacts

Data Mapping:

Input: Domain extracted from company URL
Output: Object with emails array, organization name, and domain

Success Path: → If
Error Path: Workflow continues to If node even on failure

7. If
Functionality: Conditional router that checks if any email addresses were found.
Built-in Parameters to Replicate:

Condition type: Number comparison
Operator: Not equals
Case sensitive: True
Type validation: Strict
Version: 2

Workflow-Specific Configuration:

Condition: Check if the length of emails array is not equal to 0
True branch: Process successful lookup
False branch: Log failed lookup

Data Mapping:

Input: Hunter node results
Output: Same data routed to appropriate branch

Success Path:

If emails found → Edit Fields-Prepare Update Data
If no emails → Google Sheets- Log Failed Lookups

Error Path: Routes to false branch on evaluation error

8. Google Sheets- Log Failed Lookups
Functionality: Records domains where no email addresses were found to a "Failures" sheet.
Built-in Parameters to Replicate:

Operation: Append or update
Authentication: OAuth2
Matching mode: Column matching
Update behavior: Append if not exists

Workflow-Specific Configuration:

Spreadsheet: Same as source ("Automated outbound sales")
Sheet: "Failures"
Column mapping: Store domain in "failedCompanyUrl" column

Data Mapping:

Input: Domain from Hunter node
Output: Confirmation of row added/updated

Success Path: Workflow continues to the next company.
Error Path: Workflow stops on write failure

9. Edit Fields-Prepare Update Data
Functionality: Acts as a marker node to initialize the success path. In the Python implementation, it resets the `success_logged` state.
Built-in Parameters to Replicate:

Operation: Set fields
Assignment type: Manual value mapping

Workflow-Specific Configuration:

Field assignment: Sets `success_logged` to `false`.

Data Mapping:

Input: Current execution data
Output: Object with `success_logged: false`

Success Path: → OpenAI1- email body
Error Path: Workflow stops on error

10. OpenAI1- email body
Functionality: Generates personalized cold email body using gpt-4o-mini based on company summary and contact information.
Built-in Parameters to Replicate:

Model: gpt-4o-mini
Authentication: API key
Message format: Single user message

Workflow-Specific Configuration:

Complex prompt including:

Writing style instructions (avoid purple prose, use few words)
Two example emails for style reference
Context: Company summary from summarizer, contact person's first and last name from Hunter
Signature block: "Best, Kaushalya N, Co-Founder"



Data Mapping:

Input: Company summary and Hunter contact data
Output: Generated email body in message.content

Success Path: → OpenAI- subject
Error Path: Workflow stops on API error

11. OpenAI- subject
Functionality: Generates email subject line using gpt-4o-mini.
Built-in Parameters to Replicate:

Model: gpt-4o-mini
Authentication: API key
Message format: Single user message

Workflow-Specific Configuration:

Prompt context: Company summary, organization name from Hunter, contact person name
Instructions: "Write a 3 to 4 word subject to grab their attention. Mention their company name and partnership."
Example format: "Potential Partnership with Cognizant"

Data Mapping:

Input: Company data and contact information
Output: Subject line in message.content

Success Path: → Gmail
Error Path: Workflow stops on API error

12. Gmail
Functionality: Creates a draft email in Gmail with generated content.
Built-in Parameters to Replicate:

Operation: Create draft
Authentication: OAuth2
Output format: Draft ID and status

Workflow-Specific Configuration:

Subject: Generated subject from OpenAI
Body: Generated email body from OpenAI
Recipient: First email address from Hunter results

Data Mapping:

Input: Subject and body from OpenAI nodes, email from Hunter
Output: Draft creation confirmation

Success Path: → Google Sheets - Update Success Log
Error Path: Workflow stops on Gmail API error

13. Google Sheets - Update Success Log
Functionality: Updates the original spreadsheet with successful contact information.
Built-in Parameters to Replicate:

Operation: Append or update
Authentication: OAuth2 (via service client)
Matching columns: companyUrl
Update behavior: Update if exists, append if new

Workflow-Specific Configuration:

Spreadsheet: Same as source
Sheet: "Sheet1"
Column mapping:

contactEmail: First email from Hunter
contactName: Full name from Hunter (first + last)
companyUrl: Original URL



Data Mapping:

Input: Contact data from Hunter and prepared company URL
Output: Confirmation of row updated

Success Path: Workflow continues to the next company.
Error Path: Workflow stops on write failure

Additional Express.js Implementation Requirements
Required Middleware:

Body parser for JSON/form data
CORS handling for API endpoints
Rate limiting for external API calls
Request logging middleware

External Service Dependencies:

Google Sheets API v4 with OAuth2
Gmail API with OAuth2
Hunter.io API with API key
OpenAI API with API key
HTML parsing library (e.g., cheerio)
HTTP client for website fetching

Rate Limiting Requirements:

Hunter.io API limits (check documentation)
OpenAI API rate limits
Gmail API quotas
Implement exponential backoff for all APIs

Error Handling Strategy:

Graceful degradation for non-critical failures
Detailed logging for debugging
Separate error tracking for each external service
Transaction-like behavior for Google Sheets updates

Data Validation Requirements:

URL validation for company URLs
Email validation for Hunter results
Length validation for AI-generated content
Domain extraction validation
Empty/null checks at each step