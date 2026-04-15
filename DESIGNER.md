# MUN SaaS - Design Brief for Designer

## Project Overview

**MUN SaaS** is a web-based platform for organizing and managing Model United Nations (MUN) conferences. It helps organizers manage delegate registrations, committee assignments, documents, announcements, and committee communications—all in one place.

---

## What the Platform Does

### For Organizers (Schools/Clubs Running MUN Events)
- Create and manage MUN events
- Create committees (Security Council, DISEC, UNDP, etc.)
- Add chairs/co-chairs with login credentials
- Manage delegate registrations
- Assign delegates to committees
- Upload/share documents
- Post announcements
- Committee chat rooms
- Export delegate credentials

### For Delegates (Students Participating)
- Login with credentials
- View their committee and country assignment
- Access shared documents
- Read announcements
- Chat in committee rooms

---

## Current Technical Stack

- **Frontend**: Flask + Jinja2 templates + CSS (custom design system)
- **Backend**: Convex (database + HTTP actions)
- **Hosting**: Vercel
- **Design System**: Custom CSS with design tokens, dark theme, water-inspired effects

---

## Branding Options

### Option 1: Keep "MUN SaaS"
Clean, functional, clearly communicates purpose.

### Option 2: New Names to Consider
- **ConferenceHub** - functional, professional
- **DelegateDesk** - approachable, delegate-focused
- **MUNSync** - modern, sync-related
- **ModelUN** - direct, memorable

---

## Visual Identity Requirements

### Color Palette (Official)
- Primary (CTAs, accents, active states, logo mark): `#3F8AD8` (Blue)
- Card/Panel Backgrounds (featured pricing, CTA sections): `#3F5273` (Navy)
- Section Labels, Country Tags, Supporting Text: `#8B9474` (Sage)
- Typography: `#000000` (Black)
- Page Background: `#FFFFFF` (White)

### Light Mode Design
- Background: `#FFFFFF`
- Card: `#3F5273` (Navy - for featured cards)
- Primary: `#3F8AD8` (Blue)
- Text: `#000000`
- Muted/Supporting: `#8B9474` (Sage)

### Typography
- **Headings**: DM Sans - Bold, clean
- **Body**: DM Sans - Regular
- **Mono**: Space Mono - For code/data elements

### Style Direction
- Soft structuralist with selective glass accents
- Clean, professional, academic feel
- Water-inspired ripple effects on buttons/cards
- Generous whitespace
- Not playful - reflects the formal nature of MUN

### Logo Concepts to Explore
1. **Globe + Connection** - Represents international diplomacy
2. **Committee Seating** - Visual of delegates around a table
3. **Abstract MUN** - Minimal, modern take on "MUN" letters
4. **Speech Bubble/Country Flags** - Communication-focused

---

## Key Pages for Designer Review

### 1. Dashboard (`/dashboard`)
- Welcome hero with wave animation effect
- Stats cards (events, delegates, committees)
- Upcoming events feed
- Recent announcements

### 2. Events (`/events`)
- Event cards with creation modal
- List of all events

### 3. Billing (`/events/{id}/billing`) ⭐ KEY PAGE
- Current plan display
- Plan comparison cards (Small/Medium/Large)
- Upgrade flow
- This needs professional, trustworthy design - users paying here!

### 4. Delegates List (`/events/{id}/delegates`)
- Accordion committees
- Chair/co-chair badges
- Add delegate form

### 5. Committees (`/events/{id}/committees`)
- List with creation modal

### 6. Auth Pages
- Login, Register, Forgot Password
- Consistent styling with main app

---

## Pricing Tiers (for Billing Page)

| Plan | Delegates | Price (AED) |
|------|-----------|-------------|
| Small | 0-100 | 199 |
| Medium | 101-200 | 399 |
| Large | 201+ | 500 (+2/delegate) |

---

## Technical Notes

- **Vercel URL**: https://mun-saas.vercel.app
- **Dark theme only** currently (light mode in .impeccable but not implemented)
- Responsive design (mobile-first)
- Custom CSS design system with tokens
- No framework - vanilla CSS

---

## Designer Deliverables Needed

1. **Logo** - Primary logo + favicon version
2. **Plan Cards Redesign** - Make billing page more premium/trustworthy
3. **Empty State Illustrations** - Nice graphics for empty lists
4. **Loading States** - Polished loading animations

---

## Contact

For questions about this brief, contact: [your contact info]

---

*Brief created: April 2026*
*MUN SaaS - Manage your Model United Nations conferences in one place*