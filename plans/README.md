# Plans

## `prd.json`

`prd.json` is a lightweight, JSON-based PRD/TODO list: an array of small, testable work items (similar to user stories) that the agent can pick from.

Each item typically contains:

- `category`: e.g. `functional` or `ui`
- `description`: one-line requirement/behavior
- `steps`: human-readable acceptance steps
- `passes`: boolean that flips to `true` when the work item is completed

### How it’s meant to be used

- Keep items small enough to fit in one agent iteration.

### Example

```json
[
	{
		"category": "functional",
		"description": "User can send a message and see it appear in the conversation",
		"steps": [
			"Open the chat app and navigate to a conversation",
			"Type a message in the composer",
			"Click Send (or press Enter)",
			"Verify the message appears in the message list",
			"Verify the message content matches what was typed"
		],
		"passes": false
	},
	{
		"category": "functional",
		"description": "Messages persist after refresh/reopen",
		"steps": [
			"Send a message in a conversation",
			"Refresh the page (or close and reopen the app)",
			"Navigate back to the same conversation",
			"Verify the previously sent message is still visible"
		],
		"passes": false
	},
	{
		"category": "functional",
		"description": "Real-time incoming messages appear without manual refresh",
		"steps": [
			"Open the same conversation in two browser windows (User A and User B)",
			"From User B, send a message to the conversation",
			"On User A, verify the new message appears automatically",
			"Verify ordering places the new message at the end of the conversation"
		],
		"passes": false
	},
	{
		"category": "ui",
		"description": "Conversation list shows name, last message preview, and timestamp",
		"steps": [
			"Open the chat app with existing conversations",
			"Verify each conversation row shows a title/name",
			"Verify a last-message preview is visible",
			"Verify a timestamp for the last message is visible"
		],
		"passes": false
	},
	{
		"category": "ui",
		"description": "Composer disables Send for empty message and enables when text is present",
		"steps": [
			"Open a conversation",
			"Verify the Send button is disabled when the composer is empty",
			"Type at least one character",
			"Verify the Send button becomes enabled",
			"Delete all text",
			"Verify the Send button becomes disabled again"
		],
		"passes": false
	}
]
```