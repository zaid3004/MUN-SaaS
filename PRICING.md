MUN SaaS – Pricing
🟢 Small MUN

0–100 delegates — AED 199

Features
Delegate management
Unlimited committees
Document sharing & management
Announcements
Email support (low priority)
🟡 Medium MUN ⭐

101–200 delegates — AED 399

Features
Everything in Small
Committee chat rooms
Improved document organization
Delegate activity tracking (coming soon)
Role-based dashboards (coming soon)
Email support (medium priority)
🔴 Large MUN

201+ delegates — AED 500 (includes up to 250 delegates)
+ AED 2 per additional delegate

Features
Advanced analytics dashboard (coming soon)
Exportable reports (coming soon)
Email support (high priority)
Billing Model

We use per-event billing.

Why this works
1. Product is event-based

MUNs operate in cycles:

Plan → run → finish
A recurring subscription doesn’t match this usage pattern

Forcing subscriptions at this stage creates unnecessary friction.

2. Easier to sell
Schools and student organizations budget per event
One-time pricing is easier to approve
No long-term commitment required
3. Faster revenue
Payment is collected upfront
No dependency on renewals
No early-stage churn concerns
Limitations of Per-Event Only

Per-event billing is effective now, but not sufficient long-term.

We are currently not capturing:

Recurring organizers (annual school MUNs)
Clubs running multiple events
Large organizations needing ongoing tools
Future Direction

We will introduce subscription options once we have traction:

Planned options
Monthly plan for multiple events
Annual license for schools
Unlimited event access tiers
System Enforcement Requirements

To prevent abuse and revenue leakage, the system must enforce:

Each payment is tied to exactly one event
Event access is restricted if unpaid or expired
Delegate count is tracked and validated against payment

Failure to enforce this leads to:

Reuse of a single payment across events
Undercounting delegates
Silent revenue loss
Stripe Integration (Flask)
Core Principle

We treat Stripe as the source of truth.

Payments are verified via webhooks
Access is granted only after confirmation
Frontend responses are never trusted
Data Model
User
- id
- email
- stripe_customer_id

Event
- id
- name
- owner_id
- delegate_count
- is_paid
- stripe_session_id
- stripe_payment_intent_id
- expires_at

Rule: One event = one payment.

Checkout Session (Backend)
Pricing is calculated server-side
Stripe Checkout is used for payment
Metadata links Stripe session to event and user
Webhook Enforcement
Listen for checkout.session.completed
Mark event as paid
Store payment intent ID
Set event expiration

Access is granted only after webhook confirmation.

Access Control

Every protected route must verify:

Event is paid
Event has not expired

Access is denied otherwise.

Delegate Enforcement
Delegate count is updated on each addition
Required price is recalculated
If payment is insufficient → upgrade required
Failure Handling
Listen for failed payments
Restrict access if necessary
Security Rules

Never:

Trust frontend pricing
Grant access from success page
Skip webhook verification

Always:

Verify Stripe signatures
Calculate pricing on backend
Link payments via metadata
Summary
Per-event billing is the correct approach for now
Pricing scales with delegate count
Stripe enforces all payments and access
System is designed to evolve into subscriptions later