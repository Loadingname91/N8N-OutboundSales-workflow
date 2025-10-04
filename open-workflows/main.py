import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, TypedDict
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from langgraph.graph import StateGraph, END
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("outbound_workflow")


class WorkflowState(TypedDict, total=False):
    pending_urls: List[str]
    current_company_url: str
    current_domain: str
    html_content: str
    text_content: str
    summary: str
    hunter_response: Dict[str, Any]
    contact_email: str
    contact_name: str
    subject: str
    email_body: str
    gmail_draft: Dict[str, Any]
    success_logged: bool
    failure_logged: bool
    errors: List[str]
    results: List[Dict[str, Any]]


@dataclass
class GoogleClients:
    sheets_service: Any
    gmail_service: Any


class GoogleSheetsClient:
    def __init__(self, creds: Credentials):
        self.service = build("sheets", "v4", credentials=creds)

    @retry(wait=wait_exponential(1, 60), stop=stop_after_attempt(5))
    def get_column(self, spreadsheet_id: str, range_a1: str) -> List[str]:
        result = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_a1)
            .execute()
        )
        values = result.get("values", [])
        return [row[0] for row in values if row and row[0].strip()]


class GoogleSheetsWriter:
    def __init__(self, creds: Credentials):
        self.service = build("sheets", "v4", credentials=creds)

    @retry(wait=wait_exponential(1, 60), stop=stop_after_attempt(5))
    def append_or_update(
        self,
        spreadsheet_id: str,
        range_a1: str,
        rows: List[List[Any]],
    ) -> Dict[str, Any]:
        body = {"values": rows}
        request = (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=range_a1,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body,
            )
        )
        return request.execute()


class GmailClient:
    def __init__(self, creds: Credentials):
        self.service = build("gmail", "v1", credentials=creds)

    @retry(wait=wait_exponential(1, 60), stop=stop_after_attempt(5))
    def create_draft(self, subject: str, body: str, recipient: str) -> Dict[str, Any]:
        message = {
            "raw": self._encode_rfc822(subject=subject, body=body, to=recipient),
        }
        return (
            self.service.users()
            .drafts()
            .create(userId="me", body={"message": message})
            .execute()
        )

    @staticmethod
    def _encode_rfc822(*, subject: str, body: str, to: str) -> str:
        from base64 import urlsafe_b64encode

        lines = [
            f"To: {to}",
            "Content-Type: text/plain; charset=utf-8",
            f"Subject: {subject}",
            "",
            body,
        ]
        raw_bytes = "\r\n".join(lines).encode("utf-8")
        return urlsafe_b64encode(raw_bytes).decode("utf-8")


class HunterClient:
    def __init__(self, api_key: str, http_client: Optional[httpx.Client] = None):
        self.api_key = api_key
        self.http = http_client or httpx.Client(timeout=30)

    @retry(wait=wait_exponential(1, 60), stop=stop_after_attempt(5))
    def domain_search(self, domain: str) -> Dict[str, Any]:
        response = self.http.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": domain, "api_key": self.api_key},
        )
        response.raise_for_status()
        return response.json().get("data", {})


class HtmlFetcher:
    def __init__(self, http_client: Optional[httpx.Client] = None):
        self.http = http_client or httpx.Client(
            follow_redirects=True, timeout=30)

    @retry(wait=wait_exponential(1, 60), stop=stop_after_attempt(5))
    def fetch(self, url: str) -> str:
        response = self.http.get(url)
        response.raise_for_status()
        return response.text


class OpenAIClient:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    @retry(wait=wait_exponential(1, 60), stop=stop_after_attempt(5))
    def get_completion(self, prompt: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=[{"role": "user", "content": prompt}],
        )
        return response.output[0].content[0].text


@dataclass
class WorkflowConfig:
    sheet_id: str
    sheet_range: str
    failure_sheet_range: str
    success_sheet_range: str
    hunter_api_key: str
    openai_api_key: str
    google_credentials: Credentials


def validate_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return all([parsed.scheme in ("http", "https"), parsed.netloc])
    except Exception:
        return False


def extract_domain(url: str) -> Optional[str]:
    parsed = urlparse(url)
    domain = parsed.netloc
    return domain.split(":")[0] if domain else None


def validate_email(email: str) -> bool:
    pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    return bool(re.match(pattern, email))


def manual_trigger_node(_: WorkflowState) -> WorkflowState:
    return {"pending_urls": [], "results": [], "errors": []}


def load_company_urls_node(config: WorkflowConfig, sheets_reader: GoogleSheetsClient):
    def node(state: WorkflowState) -> WorkflowState:
        urls = sheets_reader.get_column(config.sheet_id, config.sheet_range)
        valid_urls = [url for url in urls if validate_url(url)]
        invalid_urls = set(urls) - set(valid_urls)
        if invalid_urls:
            logger.warning("Skipping invalid URLs: %s", invalid_urls)
        return {"pending_urls": valid_urls}

    return node


def next_company_node(state: WorkflowState) -> WorkflowState:
    pending = state.get("pending_urls", [])
    if not pending:
        return {'current_company_url':""}
    current = pending[0]
    remaining = pending[1:]
    domain = extract_domain(current)
    if not domain:
        raise ValueError(f"Unable to extract domain from URL: {current}")
    updated_state: WorkflowState = {
        "pending_urls": remaining,
        "current_company_url": current,
        "current_domain": domain,
    }
    for key in [
        "html_content",
        "text_content",
        "summary",
        "hunter_response",
        "contact_email",
        "contact_name",
        "subject",
        "email_body",
        "gmail_draft",
        "success_logged",
        "failure_logged",
    ]:
        if key in state:
            updated_state[key] = None  # reset fields for next iteration
    return updated_state


def should_continue(state: WorkflowState) -> Literal["process", "done"]:
    return "process" if state.get("current_company_url") else "done"


def fetch_html_node(fetcher: HtmlFetcher):
    def node(state: WorkflowState) -> WorkflowState:
        url = state["current_company_url"]
        html = fetcher.fetch(url)
        return {"html_content": html}

    return node


def extract_body_text_node(state: WorkflowState) -> WorkflowState:
    html = state.get("html_content", "")
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one("body")
    text = body.get_text(separator=" ", strip=True) if body else ""
    return {"text_content": text}


def summarize_company_node(openai_client: OpenAIClient):
    def node(state: WorkflowState) -> WorkflowState:
        text_content = state.get("text_content", "")
        if not text_content:
            raise ValueError("No text content available for summarization.")
        prompt = (
            "Summarize the following website content. Focus on what the company does "
            "and its main value proposition. Keep it concise, under 75 words. "
            f"Here is the content: {text_content}"
        )
        summary = openai_client.get_completion(prompt)
        return {"summary": summary.strip()}

    return node


def hunter_lookup_node(hunter_client: HunterClient):
    def node(state: WorkflowState) -> WorkflowState:
        domain = state["current_domain"]
        hunter_data = hunter_client.domain_search(domain)
        return {"hunter_response": hunter_data}

    return node


def has_emails(state: WorkflowState) -> Literal["has_email", "no_email"]:
    emails = state.get("hunter_response", {}).get("emails", [])
    return "has_email" if emails else "no_email"


def log_failures_node(config: WorkflowConfig, sheets_writer: GoogleSheetsWriter):
    def node(state: WorkflowState) -> WorkflowState:
        domain = state.get("current_domain")
        if not domain:
            raise ValueError("Missing domain for failure logging.")
        sheets_writer.append_or_update(
            config.sheet_id,
            config.failure_sheet_range,
            [[domain]],
        )
        return {"failure_logged": True}

    return node


def prepare_success_node(state: WorkflowState) -> WorkflowState:
    return {"success_logged": False}


def select_primary_contact(hunter_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    emails = hunter_response.get("emails", []) if hunter_response else []
    return emails[0] if emails else None


def generate_email_body_node(openai_client: OpenAIClient):
    def node(state: WorkflowState) -> WorkflowState:
        hunter_data = state.get("hunter_response", {})
        summary = state.get("summary", "")
        primary_contact = select_primary_contact(hunter_data)
        if not primary_contact:
            raise ValueError("No contact available for email body generation.")
        first = primary_contact.get("first_name") or ""
        last = primary_contact.get("last_name") or ""
        prompt = (
            "AVOID PURPLE PROSE. USE AS FEW WORDS AS POSSIBLE.\n\n"
            "USE THESE FOLLOWING EXAMPLES AS THEY'RE VERY GOOD. STICK VERY CLOSE TO THIS "
            "STYLE AND EXACT TONE.\n\n"
            "EXAMPLE 1:\n\n"
            "Hey Tom,\n\n"
            "I lead the team at AgentHub.dev and found you online when looking for "
            "Intelligent Automation consultants. We're an AI-first intelligent automation platform.\n\n"
            "We're backed by the same people as AirBnB and Doordash but looking to explore collaborating with existing companies in the field.\n\n"
            "Would love to chat this week if you're open to it.\n\n"
            "EXAMPLE 2:\n\n"
            "Hey Priti,\n\n"
            "Hope this cold email is alright — found Cognizant's website and thought I'd reach out since we're building in the intelligent automation space.\n\n"
            "I lead the team at AgentHub.dev, we're an AI-first intelligent automation tool. "
            "We're backed by the same people as AirBnB and Doordash but fully focused on helping businesses automate work with AI.\n\n"
            "Would love to chat about potential collaboration if you're open to it.\n\n"
            "ALWAYS SIGN OFF WITH:\n\n"
            "-----\n"
            "Best\n"
            "Kaushalya N\n"
            "Co-Founder\n\n"
            f"Context:\nSummary of company: {summary}\n"
            f"Contact person: {first} {last}"
        )
        body = openai_client.get_completion(prompt)
        full_name = (first + " " + last).strip()
        updates: WorkflowState = {
            "email_body": body.strip(),
            "contact_name": full_name,
            "contact_email": primary_contact.get("value"),
        }
        return updates

    return node


def generate_subject_node(openai_client: OpenAIClient):
    def node(state: WorkflowState) -> WorkflowState:
        hunter_data = state.get("hunter_response", {})
        summary = state.get("summary", "")
        contact_name = state.get("contact_name", "")
        organization = hunter_data.get(
            "organization") or state.get("current_domain")
        prompt = (
            f"Context:\nSummary of company: {summary}\n"
            f"Company Name: {organization}\n"
            f"Contact person: {contact_name}\n\n"
            "Write a 3 to 4 word subject to grab their attention. Mention their company "
            "name and partnership.\n"
            "Here is an example: 'Potential Partnership with Cognizant'"
        )
        subject = openai_client.get_completion(prompt)
        return {"subject": subject.strip()}

    return node


def create_gmail_draft_node(gmail_client: GmailClient):
    def node(state: WorkflowState) -> WorkflowState:
        subject = state.get("subject")
        body = state.get("email_body")
        recipient = state.get("contact_email")
        if not (subject and body and recipient):
            raise ValueError(
                "Missing subject, body, or recipient for Gmail draft.")
        if not validate_email(recipient):
            raise ValueError(f"Invalid recipient email: {recipient}")
        draft = gmail_client.create_draft(
            subject=subject, body=body, recipient=recipient
        )
        return {"gmail_draft": draft}

    return node


def update_success_log_node(config: WorkflowConfig, sheets_writer: GoogleSheetsWriter):
    def node(state: WorkflowState) -> WorkflowState:
        contact_email = state.get("contact_email")
        contact_name = state.get("contact_name")
        company_url = state.get("current_company_url")
        if not all([contact_email, contact_name, company_url]):
            raise ValueError("Missing data for success log update.")
        rows = [[contact_email, contact_name, company_url]]
        sheets_writer.append_or_update(
            config.sheet_id, config.success_sheet_range, rows
        )
        return {"success_logged": True}

    return node


def accumulate_results_node(state: WorkflowState) -> WorkflowState:
    results = state.get("results", [])
    entry = {
        "company_url": state.get("current_company_url"),
        "domain": state.get("current_domain"),
        "contact_email": state.get("contact_email"),
        "contact_name": state.get("contact_name"),
        "subject": state.get("subject"),
        "email_body": state.get("email_body"),
        "gmail_draft_id": state.get("gmail_draft", {}).get("id"),
        "success_logged": state.get("success_logged", False),
        "failure_logged": state.get("failure_logged", False),
    }
    results.append(entry)
    return {"results": results}


def build_graph(config: WorkflowConfig) -> StateGraph:
    sheets_reader = GoogleSheetsClient(config.google_credentials)
    sheets_writer = GoogleSheetsWriter(config.google_credentials)
    gmail_client = GmailClient(config.google_credentials)
    hunter_client = HunterClient(config.hunter_api_key)
    openai_client = OpenAIClient(config.openai_api_key)
    fetcher = HtmlFetcher()

    graph = StateGraph(WorkflowState)

    graph.add_node("manual_trigger", manual_trigger_node)
    graph.add_node("load_company_urls",
                   load_company_urls_node(config, sheets_reader))
    graph.add_node("next_company", next_company_node)
    graph.add_node("fetch_html", fetch_html_node(fetcher))
    graph.add_node("extract_body_text", extract_body_text_node)
    graph.add_node("summarize_company", summarize_company_node(openai_client))
    graph.add_node("hunter_lookup", hunter_lookup_node(hunter_client))
    graph.add_node("log_failures", log_failures_node(config, sheets_writer))
    graph.add_node("prepare_success", prepare_success_node)
    graph.add_node("generate_email_body",
                   generate_email_body_node(openai_client))
    graph.add_node("generate_subject", generate_subject_node(openai_client))
    graph.add_node("create_gmail_draft", create_gmail_draft_node(gmail_client))
    graph.add_node("update_success_log",
                   update_success_log_node(config, sheets_writer))
    graph.add_node("accumulate_results", accumulate_results_node)

    graph.set_entry_point("manual_trigger")
    graph.add_edge("manual_trigger", "load_company_urls")
    graph.add_edge("load_company_urls", "next_company")
    graph.add_conditional_edges(
        "next_company", should_continue, {"process": "fetch_html", "done": END}
    )
    graph.add_edge("fetch_html", "extract_body_text")
    graph.add_edge("extract_body_text", "summarize_company")
    graph.add_edge("summarize_company", "hunter_lookup")
    graph.add_conditional_edges(
        "hunter_lookup",
        has_emails,
        {"has_email": "prepare_success", "no_email": "log_failures"},
    )
    graph.add_edge("log_failures", "next_company")
    graph.add_edge("prepare_success", "generate_email_body")
    graph.add_edge("generate_email_body", "generate_subject")
    graph.add_edge("generate_subject", "create_gmail_draft")
    graph.add_edge("create_gmail_draft", "update_success_log")
    graph.add_edge("update_success_log", "accumulate_results")
    graph.add_edge("accumulate_results", "next_company")

    return graph.compile()


def load_google_credentials() -> Credentials:
    token_json = os.getenv("GOOGLE_TOKEN_JSON")
    if not token_json:
        raise EnvironmentError("GOOGLE_TOKEN_JSON is required.")
    data = json.loads(token_json)
    return Credentials.from_authorized_user_info(
        data,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/gmail.modify",
        ],
    )


def build_config_from_env() -> WorkflowConfig:
    creds = load_google_credentials()
    return WorkflowConfig(
        sheet_id=os.environ["GOOGLE_SHEET_ID"],
        sheet_range="Sheet1!A:A",
        failure_sheet_range="Failures!A:A",
        success_sheet_range="Sheet1!B:D",
        hunter_api_key=os.environ["HUNTER_API_KEY"],
        openai_api_key=os.environ["OPENAI_API_KEY"],
        google_credentials=creds,
    )


if __name__ == "__main__":
    config = build_config_from_env()
    graph = build_graph(config)
    final_state = graph.invoke({}, {"recursion_limit": 100})
    logger.info("Workflow finished with %d items",
                len(final_state.get("results", [])))