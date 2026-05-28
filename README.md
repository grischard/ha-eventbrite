# Eventbrite for Home Assistant

Custom Home Assistant integration for displaying Eventbrite events as a calendar,
event metadata sensors, a featured-event selector, and an image entity for the
featured event logo.

## Installation with HACS

1. Add this repository as a custom HACS integration repository.
2. Install **Eventbrite** from HACS.
3. Restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration > Eventbrite**.

## Setup

Create a personal OAuth token in Eventbrite with read access to the event source
you want to display. The integration validates the token with `/v3/users/me/`.

Setup fields:

| Field | Required | Notes |
| --- | --- | --- |
| Name | Yes | Used for the device name and default entity IDs. |
| API token | Yes | Stored in the config entry and used as a Bearer token. |
| Organizer ID | One source required | Fetches `/v3/organizers/{id}/events/`. |
| Collection ID | One source required | Fetches `/v3/collections/{id}/events/` through the isolated collection client path. |
| Search query | One source required | Uses Eventbrite event search when the token/app can access it. |
| Event statuses | No | Default: `live,started`. |
| Maximum events | No | Default: `10`. |
| Scan interval | No | Default: `30` minutes. |
| Event title regex filter | No | Optional case-insensitive title filter. |

Eventbrite search and collection API access can vary by account and app. If
Eventbrite rejects those endpoints with 401/403, the config flow or coordinator
will surface that as an authentication or permission failure.

## Entities

For a setup named `my_org`, the default entities are:

- `calendar.eventbrite_my_org`
- `sensor.eventbrite_my_org_upcoming_events`
- `sensor.eventbrite_my_org_featured_event`
- `select.eventbrite_my_org_display_event`
- `image.eventbrite_my_org_featured_event_logo`

Use the calendar entity for Home Assistant calendar semantics and automations.
Use the featured-event sensor plus image entity for dashboards, eInk displays,
QR handoff screens, and richer Eventbrite metadata.

## Dashboard Example

```yaml
type: vertical-stack
cards:
  - type: picture-entity
    entity: image.eventbrite_my_org_featured_event_logo
    show_name: false
    show_state: false

  - type: markdown
    content: >-
      ## {{ states('sensor.eventbrite_my_org_featured_event') }}

      {% set starts = state_attr('sensor.eventbrite_my_org_featured_event', 'starts_at') %}
      {% if starts %}
      {{ as_datetime(starts).strftime('%A %-d %B, %-I:%M %p') }}
      {% endif %}

      {% set venue = state_attr('sensor.eventbrite_my_org_featured_event', 'venue_name') %}
      {% if venue %}
      **{{ venue }}**
      {% endif %}

      {{ state_attr('sensor.eventbrite_my_org_featured_event', 'summary') or '' }}

      {% set url = state_attr('sensor.eventbrite_my_org_featured_event', 'url') %}
      {% if url %}
      [Open on Eventbrite]({{ url }})
      {% endif %}

  - type: entities
    entities:
      - entity: select.eventbrite_my_org_display_event
```

## Rotate Featured Event

Use a Home Assistant automation to rotate the selected featured event. This keeps
the integration poll interval sensible while still allowing frequent dashboard
changes.

```yaml
alias: Rotate Eventbrite featured event
mode: single
trigger:
  - platform: time_pattern
    minutes: "/1"
action:
  - service: select.select_next
    target:
      entity_id: select.eventbrite_my_org_display_event
    data:
      cycle: true
```

## Development

```bash
uv run --extra test ruff format .
uv run --extra test ruff check .
uv run --with ty ty check
uv run --with mypy mypy custom_components tests
uv run --with bandit bandit -r custom_components
uv run --with pylint pylint custom_components tests
uv run --extra test pytest
```

The pure model tests do not require live Eventbrite access. Home Assistant tests mock the Eventbrite API client.
