<wizard-report>
# PostHog post-wizard report

The wizard has completed a deep integration of the MUN SaaS Flask project with PostHog. The Python SDK (`posthog>=3.0.0`) was added to `requirements.txt`, initialized in `app/__init__.py` using the `Posthog()` class constructor with `enable_exception_autocapture=True`, and an `atexit` shutdown hook was registered to ensure events are flushed on process exit. Environment variables `POSTHOG_PROJECT_TOKEN` and `POSTHOG_HOST` were written to `.env`. Twelve events were instrumented across the authentication and event-management flows in `app/routes.py`, covering user acquisition, organizer activation, content creation, and engagement. Person properties (role) are set on login and registration via `posthog_client.set()`. Error tracking via `capture_exception()` was added to all critical mutation paths.

| Event | Description | File |
|---|---|---|
| `organizer_registered` | Fired when a new organizer successfully registers an account | `app/routes.py` |
| `user_logged_in` | Fired when a user successfully logs in | `app/routes.py` |
| `login_failed` | Fired when a login attempt fails with invalid credentials | `app/routes.py` |
| `event_created` | Fired when an organizer creates a new MUN event | `app/routes.py` |
| `event_updated` | Fired when an organizer updates an existing event | `app/routes.py` |
| `event_deleted` | Fired when an organizer deletes an event | `app/routes.py` |
| `committee_created` | Fired when a committee is added to an event | `app/routes.py` |
| `delegate_added` | Fired when a new delegate is added to an event | `app/routes.py` |
| `announcement_created` | Fired when an announcement is posted for an event | `app/routes.py` |
| `chat_message_sent` | Fired when a user sends a chat message in an event | `app/routes.py` |
| `password_reset_requested` | Fired when a user requests a password reset | `app/routes.py` |
| `delegate_passwords_exported` | Fired when an organizer exports delegate passwords as CSV | `app/routes.py` |

## Next steps

We've built some insights and a dashboard for you to keep an eye on user behavior, based on the events we just instrumented:

- **Dashboard — Analytics basics**: https://us.posthog.com/project/382294/dashboard/1468066
- **New Registrations & Logins (Daily)**: https://us.posthog.com/project/382294/insights/4GflGrC7
- **Organizer Activation Funnel** (Registered → Created Event → Created Committee): https://us.posthog.com/project/382294/insights/dGhz4m2h
- **Event Management Activity** (created / updated / deleted): https://us.posthog.com/project/382294/insights/zwyn1lsy
- **Engagement Actions Breakdown** (delegates, committees, announcements, chat): https://us.posthog.com/project/382294/insights/aJ4sqB1W
- **Login Success vs Failure Rate**: https://us.posthog.com/project/382294/insights/BLjltS43

### Agent skill

We've left an agent skill folder in your project at `.claude/skills/integration-flask/`. You can use this context for further agent development when using Claude Code. This will help ensure the model provides the most up-to-date approaches for integrating PostHog.

</wizard-report>
