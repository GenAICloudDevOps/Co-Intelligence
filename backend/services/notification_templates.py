from __future__ import annotations

from typing import Any, TypedDict


class EmailTemplate(TypedDict):
    subject: str
    body: str


class SlackTemplate(TypedDict):
    title: str
    message: str
    color: str


EMAIL_PREFIX = "Co-Intelligence"
EMAIL_FOOTER = "\n\nThanks,\nCo-Intelligence"


TEMPLATES: dict[str, dict[str, dict[str, str]]] = {
    "barista_order_confirmed": {
        "email": {
            "subject": "Barista order confirmed (Order #{order_id})",
            "body": (
                "Hi {username},\n\n"
                "Your coffee order is confirmed (Order #{order_id}).\n\n"
                "Items:\n{items_summary}\n\n"
                "Total: ${total:.2f}{link_line}"
            ),
        },
        "slack": {
            "title": "Agentic Barista - New Order",
            "message": (
                "New order confirmed.\n\n"
                "*Order ID:* #{order_id}\n"
                "*Customer:* {username}\n"
                "*Total:* ${total:.2f}\n"
                "*Items:* {items_count}"
            ),
            "color": "#F59E0B",
        },
    },
    "lms_enrollment_confirmed": {
        "email": {
            "subject": "Course enrollment confirmed",
            "body": (
                "Hi {username},\n\n"
                "You are enrolled in {course_title}.\n"
                "Category: {category}\n"
                "Difficulty: {difficulty}{link_line}"
            ),
        },
        "slack": {
            "title": "Agentic LMS - New Enrollment",
            "message": (
                "New enrollment confirmed.\n\n"
                "*Course:* {course_title}\n"
                "*Student:* {username}\n"
                "*Difficulty:* {difficulty}"
            ),
            "color": "#10B981",
        },
    },
    "insurance_policy_created": {
        "email": {
            "subject": "Insurance policy created",
            "body": (
                "Hi {username},\n\n"
                "Your policy has been created.\n"
                "Policy Number: {policy_number}\n"
                "Vehicle: {vehicle_year} {vehicle_make} {vehicle_model}\n"
                "Coverage: ${coverage_amount:,.0f}{link_line}"
            ),
        },
        "slack": {
            "title": "Insurance Claims - Policy Created",
            "message": (
                "New policy created.\n\n"
                "*Policy:* {policy_number}\n"
                "*Customer:* {username}\n"
                "*Vehicle:* {vehicle_year} {vehicle_make} {vehicle_model}\n"
                "*Coverage:* ${coverage_amount:,.0f}"
            ),
            "color": "#10B981",
        },
    },
    "insurance_claim_filed": {
        "email": {
            "subject": "Insurance claim filed",
            "body": (
                "Hi {username},\n\n"
                "Your claim has been filed.\n"
                "Claim Number: {claim_number}\n"
                "Policy: {policy_number}\n"
                "Location: {incident_location}\n"
                "Incident: {incident_description}{link_line}"
            ),
        },
        "slack": {
            "title": "Insurance Claims - Claim Filed",
            "message": (
                "New claim filed.\n\n"
                "*Claim:* {claim_number}\n"
                "*Policy:* {policy_number}\n"
                "*Customer:* {username}\n"
                "*Location:* {incident_location}"
            ),
            "color": "#EF4444",
        },
    },
    "data_analysis_run_completed": {
        "email": {
            "subject": "Data analysis pipeline {status_label}",
            "body": (
                "Hi {username},\n\n"
                "Your data analysis pipeline has {status_label}.\n"
                "Dataset: {dataset_name}\n"
                "Run ID: {run_id}\n"
                "Execution: {execution_status}{link_line}"
            ),
        },
        "slack": {
            "title": "Data Analysis - Pipeline Update",
            "message": (
                "Data analysis pipeline {status_label}.\n\n"
                "*Run ID:* {run_id}\n"
                "*Dataset:* {dataset_name}\n"
                "*Source:* {source_type}\n"
                "*Status:* {status_label}"
            ),
            "color": "{status_color}",
        },
    },
    "fine_tuning_train_completed": {
        "email": {
            "subject": "LLM fine-tuning training {status_label}",
            "body": (
                "Hi {username},\n\n"
                "Your fine-tuning training job has {status_label}.\n"
                "Workflow: {workflow_label}\n"
                "Job: {job_key}\n"
                "Run ID: {run_id}\n"
                "Model: {model_name}\n"
                "Dataset: {dataset_path}\n"
                "Exit code: {exit_code}\n"
                "Finished at: {finished_at}{link_line}"
            ),
        },
        "slack": {
            "title": "LLMs Fine-Tuning - Job Update",
            "message": (
                "Fine-tuning job {status_label}.\n\n"
                "*Run ID:* {run_id}\n"
                "*Model:* {model_name}\n"
                "*Workflow:* {workflow_label}\n"
                "*Status:* {status_label}"
            ),
            "color": "{status_color}",
        },
    },
}


class TemplateError(RuntimeError):
    pass


def _format(template: str, data: dict[str, Any]) -> str:
    try:
        return template.format(**data)
    except KeyError as exc:
        raise TemplateError(f"Missing template data: {exc}") from exc


def render_email(event_type: str, data: dict[str, Any]) -> tuple[str, str]:
    template = TEMPLATES.get(event_type, {}).get("email")
    if not template:
        raise TemplateError(f"Email template not found: {event_type}")
    subject = _format(template["subject"], data)
    if not subject.startswith(EMAIL_PREFIX):
        subject = f"{EMAIL_PREFIX} | {subject}"
    body = _format(template["body"], data)
    if EMAIL_FOOTER not in body:
        body = body.rstrip() + EMAIL_FOOTER
    return subject, body


def render_slack(event_type: str, data: dict[str, Any]) -> tuple[str, str, str]:
    template = TEMPLATES.get(event_type, {}).get("slack")
    if not template:
        raise TemplateError(f"Slack template not found: {event_type}")
    title = _format(template["title"], data)
    message = _format(template["message"], data)
    color = _format(template["color"], data)
    return title, message, color
