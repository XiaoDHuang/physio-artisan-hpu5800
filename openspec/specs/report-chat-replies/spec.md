# report-chat-replies Specification

## Purpose

改进报告意图 Chat 回复文案、任务进度展示与前端轮询/门控交互。

## Requirements

### Requirement: Report intent reply SHALL be user-facing

When `POST /chat` returns `intent=report`, the `reply` field SHALL use natural Chinese and SHALL NOT contain `task_id`, UUIDs, or API path names such as `/status`.

The `reply` SHALL reference the report anchor date in a human-readable form (e.g. `6月15日` or `今天` when anchor is today) and SHALL set expectation that generation takes about 1–2 minutes.

#### Scenario: User triggers report from report page

- **WHEN** the client sends `intent=report` with `date=2026-06-15`
- **THEN** `reply` includes a friendly date label for June 15
- **AND** `reply` does not include the raw `task_id` value
- **AND** `task_id` is still returned as a structured field for polling

#### Scenario: LLM provides a custom lead sentence

- **WHEN** intent routing returns a non-empty `reply`
- **THEN** the server MAY use it as the opening sentence
- **AND** still appends a brief waiting expectation without technical details

### Requirement: Task status messages SHALL be safe for UI

Background assessment tasks SHALL expose progress via `/status` using messages suitable for end users.

When a task fails, the `message` returned to clients SHALL NOT contain raw exception text or stack traces; detailed errors SHALL be logged server-side only.

#### Scenario: Task fails during LangGraph run

- **WHEN** `GET /status/{task_id}` returns `status=failed`
- **THEN** `message` is a generic retry hint
- **AND** does not contain substrings like `Traceback` or `Exception:`

### Requirement: Frontend SHALL show report generation progress

While polling `/status` after `intent=report`, the chat UI SHALL indicate that generation is in progress distinct from the initial "thinking" state.

The client SHALL map `status` and `progress` to user-facing progress phrases and SHALL update them during polling without appending immutable duplicate lines on every tick.

#### Scenario: Long-running report

- **WHEN** polling remains in `processing` for multiple intervals
- **THEN** the user sees updating progress text (e.g. assessment → coaching → nutrition)
- **AND** the UI shows a generating state until completion, failure, or timeout

### Requirement: Terminal chat messages SHALL reflect anchor date and refresh outcome

On successful report generation, when the user has not started another chat turn (`lastIntent === 'report'`), the client MAY update `lastReply` with a success message mentioning the anchor date.

The client SHALL always show success or failure via toast and/or banner. Dashboard reload SHALL occur only when the current report page date equals the task anchor date.

On failure or timeout, messages SHALL remain user-friendly and SHALL NOT surface raw server exception strings.

#### Scenario: Report completes for selected historical date

- **WHEN** polling returns `status=completed` for `anchor_date=2026-06-10`
- **AND** the dashboard is viewing `2026-06-10`
- **THEN** the dashboard reloads and success feedback mentions `6月10日` (or equivalent)
- **AND** hints the user to scroll up to view updated advice when chat display still shows the report turn

#### Scenario: Report completes while user is viewing another date

- **WHEN** polling returns `status=completed` for anchor date D1
- **AND** the dashboard is viewing date D2 ≠ D1
- **THEN** the client shows an informational toast to switch to D1
- **AND** does not reload dashboard for D2

#### Scenario: Report times out after max polls

- **WHEN** polling exhausts the configured retry budget without `completed`
- **THEN** the user sees a timeout message that allows continued browsing
- **AND** is told to refresh or switch date later to see results

### Requirement: Report task SHALL be decoupled from single-turn chat UI

The client SHALL track an `activeReportTask` (task id, user id, anchor date, progress) independently of `lastReply`.

Polling SHALL NOT block subsequent `send()` calls for non-report intents.

#### Scenario: User sends data entry while report is running

- **WHEN** `activeReportTask.status` is `running`
- **AND** the user sends a message that resolves to `data_entry` or `other`
- **THEN** the client posts `/chat` normally and updates `lastReply` with that response
- **AND** report progress continues to update via banner
- **AND** on report completion the client SHALL NOT append success text to `lastReply` if `lastIntent` is not `report`

### Requirement: Changing report dashboard date SHALL clear chat display only

When the user changes the report page anchor date via header navigation while a report task is still running, the client SHALL clear chat display state (`lastReply`, `lastQuestion`, `lastIntent`) without cancelling the background task or stopping status polling.

The client SHALL retain `conversationId` and `activeReportTask`.

#### Scenario: User switches date during generation

- **WHEN** report generation was started for anchor date D1
- **AND** the user navigates the dashboard to date D2 before the task completes
- **THEN** chat display is cleared
- **AND** background polling continues for D1
- **WHEN** the task completes and the dashboard is still on D2
- **THEN** the client shows an informational toast that D1 report is ready and does not call dashboard load for D2
- **WHEN** the task completes and the dashboard is on D1
- **THEN** the client reloads dashboard data for D1 and shows success feedback

### Requirement: Duplicate report requests SHALL be blocked on the client

While `activeReportTask` is running for a user, the client SHALL reject new report-generation attempts before calling `POST /chat` and SHALL show a friendly wait message referencing the in-flight anchor date.

Server-side task deduplication is out of scope for this change.

#### Scenario: User asks to generate report again

- **WHEN** `activeReportTask.status` is `running`
- **AND** the user sends another report-generation message or clicks a report suggestion chip
- **THEN** no new `/chat` report request is sent
- **AND** the user sees a message such as「{date}的报告正在生成中，请稍候再试」
