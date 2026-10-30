# Atharva ITS - Service Desk Playbook

Internal notes for service desk engineers.

## Email Not Working

First find out if it's one person or many. Check the service status page and the #it-status
channel. For a single user: sign out and back in, check the mailbox isn't full, and try
Outlook on the web. If several users report the same thing, don't ask everyone to reinstall
Outlook. Log it as a possible incident and escalate to the on-call engineer.

## Slow Laptop

Check in this order: free disk space, CPU and memory usage, apps that start at login, pending
Windows updates, and whether an antivirus scan is running. Never disable the security agent as
a quick fix. If hardware diagnostics fail, or the laptop keeps shutting down after the
software fixes, book a hardware replacement.

## New Joiner Setup

Laptops for new joiners are prepared two working days before the start date. The joiner gets
their email, VPN access and the standard software bundle on day one. Extra tools are requested
by the manager through the Self-Service Portal.

## Ticket Priority

| Priority | When to use | Response target |
| -------- | ----------- | --------------- |
| P1 | Company-wide outage or a security incident | 15 minutes |
| P2 | A whole team blocked, no workaround | 1 hour |
| P3 | One person blocked or slowed down, some workaround exists | 4 hours |
| P4 | Requests, questions and low-impact issues | 2 working days |
