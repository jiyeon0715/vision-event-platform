from __future__ import annotations

import json
import os
from html import escape
from pathlib import Path
from urllib.parse import quote


def render_dashboard_html(
    *,
    service_status: str,
    db_path: Path,
    camera_id: str | None,
    today_event_count: int,
    event_count_by_rule_name: dict[str, int],
    event_count_by_camera_id: dict[str, int],
    latest_event_timestamp: str | None,
    camera_health_rows: list[dict],
    latest_event_rows: list[dict],
) -> str:
    bootstrap = {
        "serviceStatus": service_status,
        "dbPath": str(db_path),
        "cameraId": camera_id,
        "todayEventCount": today_event_count,
        "ruleCounts": event_count_by_rule_name,
        "cameraCounts": event_count_by_camera_id,
        "latestEventTimestamp": latest_event_timestamp,
        "cameraHealth": camera_health_rows,
        "latestEvents": latest_event_rows,
    }
    html = _dashboard_template()
    replacements = {
        "__BOOTSTRAP_JSON__": _json_script(bootstrap),
        "__TODAY_EVENT_COUNT__": str(today_event_count),
        "__SERVICE_STATUS__": _html(service_status),
        "__DB_PATH__": _html(str(db_path)),
        "__CAMERA_ID__": _html(camera_id or ""),
        "__RULE_ROWS__": _render_count_rows(event_count_by_rule_name, "rule_name"),
        "__CAMERA_ROWS__": _render_count_rows(event_count_by_camera_id, "camera_id"),
        "__HEALTH_ROWS__": _render_camera_health_rows(camera_health_rows),
        "__EVENT_ROWS__": _render_latest_event_rows(latest_event_rows),
        "__LAST_UPDATED__": _html(latest_event_timestamp or "No events yet"),
    }
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)
    return html


def _dashboard_template() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Vision Events Dashboard</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #08111f;
      --sidebar: #0a1424;
      --panel: #1d2a3e;
      --panel-soft: #202f45;
      --panel-strong: #172338;
      --border: #29384f;
      --border-soft: rgba(148, 163, 184, 0.16);
      --text: #dbe4f0;
      --muted: #7d8ca3;
      --faint: #53637a;
      --accent: #3b82f6;
      --accent-soft: rgba(59, 130, 246, 0.18);
      --success: #19d37b;
      --warning: #f5c400;
      --danger: #ff5a66;
      --orange: #ff7a1a;
      --purple: #8b5cf6;
      --shadow: 0 16px 40px rgba(0, 0, 0, 0.24);
      --radius: 8px;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }

    button, input, select {
      font: inherit;
    }

    button, a, input, select, tr[tabindex] {
      outline: none;
    }

    button:focus-visible, a:focus-visible, input:focus-visible, select:focus-visible, tr[tabindex]:focus-visible {
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.45);
    }

    .app-shell {
      display: grid;
      grid-template-columns: 212px 1fr;
      min-height: 100vh;
    }

    .sidebar {
      position: sticky;
      top: 0;
      height: 100vh;
      display: flex;
      flex-direction: column;
      background: var(--sidebar);
      border-right: 1px solid var(--border);
    }

    .brand {
      display: flex;
      gap: 12px;
      align-items: center;
      padding: 16px;
      border-bottom: 1px solid var(--border);
    }

    .brand-mark {
      width: 32px;
      height: 32px;
      display: grid;
      place-items: center;
      border-radius: 999px;
      background: #2563eb;
      color: white;
      font-weight: 800;
    }

    .brand strong {
      display: block;
      font-size: 16px;
      line-height: 1.1;
    }

    .brand span, .user span {
      color: var(--muted);
      font-size: 13px;
    }

    .nav {
      padding: 16px 8px;
    }

    .nav-title {
      margin: 0 0 10px;
      color: var(--faint);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.04em;
    }

    .nav a {
      display: flex;
      align-items: center;
      gap: 10px;
      min-height: 42px;
      padding: 0 12px;
      border-radius: var(--radius);
      color: #93a4bc;
      text-decoration: none;
      font-weight: 700;
      transition: background 150ms ease, color 150ms ease;
    }

    .nav a.active, .nav a:hover {
      background: #112957;
      color: #4a93ff;
    }

    .nav svg {
      width: 16px;
      height: 16px;
    }

    .nav-count {
      margin-left: auto;
      min-width: 28px;
      padding: 2px 7px;
      border-radius: 999px;
      background: rgba(249, 115, 22, 0.22);
      color: #fb923c;
      text-align: center;
      font-size: 12px;
    }

    .sidebar-bottom {
      margin-top: auto;
      padding: 12px 8px;
      border-top: 1px solid var(--border);
    }

    .user {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 12px 8px;
    }

    .content {
      min-width: 0;
    }

    .topbar {
      height: 62px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 0 22px;
      border-bottom: 1px solid var(--border);
      background: #0f1a2c;
    }

    .topbar h1 {
      margin: 0;
      font-size: 17px;
      line-height: 1.25;
    }

    .topbar p {
      margin: 2px 0 0;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }

    .top-actions {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 10px;
      min-width: 0;
    }

    .status-pill, .clock-pill, .icon-button, .search-field, .select-control {
      border: 1px solid var(--border);
      background: #121f33;
      color: var(--muted);
      border-radius: 12px;
      min-height: 36px;
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 0 12px;
      font-weight: 800;
      white-space: nowrap;
    }

    .dot {
      width: 7px;
      height: 7px;
      border-radius: 999px;
      background: var(--success);
      display: inline-block;
      box-shadow: 0 0 0 4px rgba(25, 211, 123, 0.12);
    }

    .clock-pill {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 0 12px;
      font-weight: 800;
      white-space: nowrap;
    }

    .icon-button {
      width: 36px;
      display: inline-grid;
      place-items: center;
      cursor: pointer;
      transition: transform 150ms ease, border-color 150ms ease, background 150ms ease;
    }

    .icon-button:hover {
      transform: translateY(-1px);
      border-color: #3a4b65;
      background: #16263d;
    }

    .main {
      padding: 14px 22px 28px;
    }

    .page-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 18px;
    }

    .page-header h2 {
      margin: 0;
      font-size: 18px;
    }

    .page-header p {
      margin: 2px 0 0;
      color: var(--muted);
      font-size: 14px;
      font-weight: 700;
    }

    .toolbar {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 8px;
    }

    .search-field {
      width: 152px;
      padding: 0 12px;
    }

    .select-control {
      padding: 0 12px;
      cursor: pointer;
    }

    .summary-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }

    .card, .section {
      background: var(--panel);
      border: 1px solid var(--border-soft);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }

    .card {
      min-height: 134px;
      padding: 18px;
      transition: transform 150ms ease, border-color 150ms ease;
    }

    .card:hover, .section:hover {
      border-color: rgba(148, 163, 184, 0.28);
    }

    .card:hover {
      transform: translateY(-1px);
    }

    .card-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    .label {
      margin: 0;
      color: #91a0b6;
      font-size: 14px;
      font-weight: 800;
    }

    .metric-icon {
      width: 32px;
      height: 32px;
      display: grid;
      place-items: center;
      border-radius: 999px;
      background: rgba(59, 130, 246, 0.14);
      color: var(--accent);
    }

    .metric-icon.danger {
      background: rgba(255, 90, 102, 0.14);
      color: var(--danger);
    }

    .metric-icon.purple {
      background: rgba(139, 92, 246, 0.14);
      color: var(--purple);
    }

    .metric-icon.success {
      background: rgba(25, 211, 123, 0.14);
      color: var(--success);
    }

    .value {
      margin: 18px 0 0;
      font-size: 30px;
      font-weight: 900;
      letter-spacing: 0;
    }

    .subvalue {
      margin: 2px 0 0;
      color: var(--faint);
      font-size: 14px;
      font-weight: 800;
    }

    .charts-grid {
      display: grid;
      grid-template-columns: minmax(320px, 1fr) minmax(320px, 1fr);
      gap: 12px;
      margin-bottom: 16px;
    }

    .section {
      overflow: hidden;
    }

    .section-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      padding: 18px 18px 8px;
    }

    .section-title {
      margin: 0;
      font-size: 18px;
      line-height: 1.2;
    }

    .section-subtitle {
      margin: 4px 0 0;
      color: var(--faint);
      font-weight: 800;
      font-size: 14px;
    }

    .chart-body {
      min-height: 206px;
      display: grid;
      grid-template-columns: 200px 1fr;
      gap: 20px;
      align-items: center;
      padding: 6px 18px 18px;
    }

    .donut {
      width: 176px;
      aspect-ratio: 1;
      border-radius: 50%;
      background: conic-gradient(var(--border) 0deg 360deg);
      position: relative;
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.04);
    }

    .donut::after {
      content: "";
      position: absolute;
      inset: 34px;
      border-radius: 50%;
      background: var(--panel);
    }

    .legend {
      display: grid;
      gap: 10px;
    }

    .legend button {
      width: 100%;
      display: grid;
      grid-template-columns: 14px 1fr auto auto;
      gap: 8px;
      align-items: center;
      border: 0;
      padding: 2px 0;
      background: transparent;
      color: var(--muted);
      text-align: left;
      cursor: pointer;
      border-radius: 6px;
    }

    .legend button:hover, .legend button.active {
      color: var(--text);
    }

    .legend-dot {
      width: 8px;
      height: 8px;
      border-radius: 999px;
    }

    .legend strong {
      color: var(--text);
    }

    .bar-chart {
      display: grid;
      grid-template-columns: auto 1fr auto;
      align-items: center;
      gap: 10px;
      padding: 6px 18px 24px;
      min-height: 220px;
    }

    .bar-label {
      color: var(--muted);
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
      font-weight: 800;
      white-space: nowrap;
    }

    .bar-track {
      height: 14px;
      border-radius: 4px;
      background: rgba(15, 23, 42, 0.4);
      overflow: hidden;
    }

    .bar {
      height: 100%;
      min-width: 2px;
      border: 0;
      border-radius: 4px;
      background: var(--accent);
      cursor: pointer;
      transition: filter 150ms ease, transform 150ms ease;
    }

    .bar:hover, .bar.active {
      filter: brightness(1.18);
      transform: scaleY(1.12);
    }

    .bar-value {
      color: var(--faint);
      min-width: 32px;
      text-align: right;
      font-size: 12px;
      font-weight: 800;
    }

    .table-wrap {
      overflow-x: auto;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 860px;
    }

    th, td {
      border-top: 1px solid rgba(148, 163, 184, 0.08);
      padding: 12px 18px;
      text-align: left;
      vertical-align: middle;
    }

    th {
      color: var(--faint);
      font-size: 13px;
      font-weight: 900;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      background: rgba(15, 23, 42, 0.1);
    }

    td {
      color: #cbd5e1;
      font-weight: 750;
    }

    tbody tr {
      transition: background 120ms ease;
    }

    tbody tr:hover {
      background: rgba(59, 130, 246, 0.06);
    }

    .muted {
      color: var(--muted);
    }

    .mono {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-weight: 800;
    }

    .status-badge, .severity-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 24px;
      padding: 0 9px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 900;
    }

    .status-badge.online {
      color: var(--success);
    }

    .status-badge.warning {
      color: var(--warning);
    }

    .status-badge.offline, .severity-badge.critical {
      color: var(--danger);
    }

    .severity-badge {
      border: 1px solid rgba(148, 163, 184, 0.2);
      background: rgba(148, 163, 184, 0.08);
    }

    .severity-badge.critical {
      border-color: rgba(255, 90, 102, 0.35);
      background: rgba(255, 90, 102, 0.12);
    }

    .severity-badge.high {
      color: #fb923c;
      border-color: rgba(251, 146, 60, 0.35);
      background: rgba(251, 146, 60, 0.12);
    }

    .severity-badge.medium {
      color: var(--warning);
      border-color: rgba(245, 196, 0, 0.35);
      background: rgba(245, 196, 0, 0.1);
    }

    .snapshot-link {
      display: inline-flex;
      border: 1px solid var(--border);
      border-radius: 6px;
      overflow: hidden;
      background: #0f172a;
    }

    .snapshot-thumb {
      width: 88px;
      height: 56px;
      object-fit: cover;
      display: block;
    }

    .action-button {
      min-height: 32px;
      border: 1px solid rgba(59, 130, 246, 0.35);
      border-radius: 999px;
      background: rgba(59, 130, 246, 0.12);
      color: #60a5fa;
      padding: 0 14px;
      font-weight: 900;
      cursor: pointer;
    }

    .filters {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      padding: 0 18px 14px;
    }

    .filters .search-field {
      width: 220px;
    }

    .pagination {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 10px;
      padding: 14px 18px 18px;
      border-top: 1px solid rgba(148, 163, 184, 0.08);
    }

    .empty {
      margin: 0;
      padding: 30px 18px;
      color: var(--muted);
      font-weight: 800;
      text-align: center;
    }

    .empty-illustration {
      display: grid;
      place-items: center;
      width: 48px;
      height: 48px;
      margin: 0 auto 10px;
      border-radius: 999px;
      background: rgba(59, 130, 246, 0.12);
      color: #60a5fa;
    }

    .skeleton {
      position: relative;
      overflow: hidden;
      min-height: 18px;
      border-radius: 6px;
      background: rgba(148, 163, 184, 0.12);
    }

    .skeleton::after {
      content: "";
      position: absolute;
      inset: 0;
      transform: translateX(-100%);
      background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.08), transparent);
      animation: shimmer 1.2s infinite;
    }

    @keyframes shimmer {
      100% { transform: translateX(100%); }
    }

    .spinner {
      width: 16px;
      height: 16px;
      border: 2px solid rgba(148, 163, 184, 0.25);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 800ms linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .toast-region {
      position: fixed;
      right: 18px;
      bottom: 18px;
      z-index: 30;
      display: grid;
      gap: 8px;
    }

    .toast {
      width: min(360px, calc(100vw - 36px));
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: #111f32;
      box-shadow: var(--shadow);
      padding: 12px 14px;
      color: var(--text);
      font-weight: 800;
    }

    .detail-panel {
      position: fixed;
      inset: 0 0 0 auto;
      z-index: 25;
      width: min(460px, 100vw);
      background: #0f1a2c;
      border-left: 1px solid var(--border);
      box-shadow: -24px 0 42px rgba(0, 0, 0, 0.28);
      transform: translateX(100%);
      transition: transform 180ms ease;
      display: flex;
      flex-direction: column;
    }

    .detail-panel.open {
      transform: translateX(0);
    }

    .panel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 18px;
      border-bottom: 1px solid var(--border);
    }

    .panel-header h3 {
      margin: 0;
      font-size: 18px;
    }

    .panel-body {
      overflow: auto;
      padding: 18px;
    }

    .panel-image {
      width: 100%;
      aspect-ratio: 16 / 10;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      object-fit: cover;
      background: #0b1220;
    }

    .detail-list {
      display: grid;
      grid-template-columns: 130px 1fr;
      gap: 10px 14px;
      margin: 18px 0;
    }

    .detail-list dt {
      color: var(--muted);
      font-weight: 900;
    }

    .detail-list dd {
      margin: 0;
      min-width: 0;
      overflow-wrap: anywhere;
      font-weight: 800;
    }

    .json-box {
      max-height: 230px;
      overflow: auto;
      padding: 12px;
      border-radius: var(--radius);
      background: #08111f;
      border: 1px solid var(--border);
      color: #cbd5e1;
      font-size: 12px;
    }

    .panel-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .visually-hidden {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }

    @media (max-width: 1100px) {
      .summary-grid, .charts-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }

    @media (max-width: 760px) {
      .app-shell {
        grid-template-columns: 1fr;
      }

      .sidebar {
        position: static;
        height: auto;
      }

      .nav {
        display: none;
      }

      .topbar {
        height: auto;
        align-items: flex-start;
        flex-direction: column;
        padding: 14px;
      }

      .top-actions {
        width: 100%;
        justify-content: flex-start;
        flex-wrap: wrap;
      }

      .main {
        padding: 14px;
      }

      .page-header {
        flex-direction: column;
      }

      .summary-grid, .charts-grid {
        grid-template-columns: 1fr;
      }

      .chart-body {
        grid-template-columns: 1fr;
        justify-items: center;
      }
    }
  </style>
</head>
<body>
  <div class="app-shell">
    <aside class="sidebar" aria-label="Primary navigation">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true">⊙</div>
        <div><strong>VisionGuard</strong><span>Safety Platform</span></div>
      </div>
      <nav class="nav">
        <p class="nav-title">MONITOR</p>
        <a class="active" href="/dashboard" aria-current="page">▦ Dashboard</a>
        <a href="#events">⚠ Events <span class="nav-count" id="nav-alert-count">0</span></a>
        <a href="#statistics">▥ Statistics</a>
        <a href="#cameras">▣ Cameras</a>
        <a href="#rules">◇ Rules</a>
        <a href="#snapshots">▱ Snapshots</a>
      </nav>
      <div class="sidebar-bottom">
        <a class="nav-link" href="#settings">⚙ Settings</a>
        <div class="user"><div class="brand-mark" aria-hidden="true">O</div><div><strong>Ops Manager</strong><span>admin@site-a.com</span></div></div>
      </div>
    </aside>

    <div class="content">
      <header class="topbar">
        <div>
          <h1>AI Vision Event Platform</h1>
          <p>Site A · Industrial Complex · Building 3</p>
        </div>
        <div class="top-actions">
          <div class="status-pill" aria-label="Service status"><span class="dot"></span><span id="system-status">Systems Operational</span></div>
          <div class="clock-pill"><span id="clock">--:--:--</span><span class="muted">| Thu, Jul 2</span></div>
          <button class="icon-button" id="refresh-button" type="button" aria-label="Refresh dashboard">↻</button>
          <button class="icon-button" type="button" aria-label="Notifications">♢</button>
        </div>
      </header>

      <main class="main">
        <!-- SQLite database: __DB_PATH__ -->
        <section class="page-header">
          <div>
            <h2>Safety Overview</h2>
            <p id="last-updated">Last updated __LAST_UPDATED__ · Auto-refresh every 30 s</p>
          </div>
          <div class="toolbar">
            <label class="visually-hidden" for="global-search">Search events</label>
            <input class="search-field" id="global-search" type="search" placeholder="Search events" aria-label="Search events">
            <select class="select-control" id="quick-range" aria-label="Time range"><option>Today</option></select>
          </div>
        </section>

        <section class="summary-grid" aria-label="Service summary">
          <!-- <p class="value">__TODAY_EVENT_COUNT__</p> -->
          <article class="card">
            <div class="card-head"><p class="label">Today's Events</p><span class="metric-icon" aria-hidden="true">⌁</span></div>
            <p class="value" data-kpi="todayEvents">__TODAY_EVENT_COUNT__</p>
            <p class="subvalue">Today total events</p>
          </article>
          <article class="card">
            <div class="card-head"><p class="label">Active Alerts</p><span class="metric-icon danger" aria-hidden="true">△</span></div>
            <p class="value" data-kpi="activeAlerts">0</p>
            <p class="subvalue" data-kpi-sub="activeAlerts">0 Critical · 0 High</p>
          </article>
          <article class="card">
            <div class="card-head"><p class="label">Active Cameras</p><span class="metric-icon purple" aria-hidden="true">▣</span></div>
            <p class="value" data-kpi="activeCameras">0</p>
            <p class="subvalue" data-kpi-sub="activeCameras">0 degraded · 0 new</p>
          </article>
          <article class="card">
            <div class="card-head"><p class="label">Online Cameras</p><span class="metric-icon success" aria-hidden="true">↯</span></div>
            <p class="value" data-kpi="onlineCameras">0 / 0</p>
            <p class="subvalue" data-kpi-sub="onlineCameras">0 offline · 0 warning</p>
          </article>
        </section>

        <section class="charts-grid" id="statistics">
          <article class="section" id="rules">
            <!-- Events By Rule -->
            <div class="section-header">
              <div><h3 class="section-title">Events by Rule</h3><p class="section-subtitle" id="rule-subtitle">Today · __TODAY_EVENT_COUNT__ total detections</p></div>
            </div>
            <div class="chart-body">
              <div class="donut" id="rule-donut" role="img" aria-label="Events by rule donut chart"></div>
              <div class="legend" id="rule-legend">__RULE_ROWS__</div>
            </div>
          </article>
          <article class="section">
            <!-- Events By Camera -->
            <div class="section-header">
              <div><h3 class="section-title">Events by Camera</h3><p class="section-subtitle" id="camera-subtitle">Today · all cameras</p></div>
            </div>
            <div class="bar-chart" id="camera-bars">__CAMERA_ROWS__</div>
          </article>
        </section>

        <section class="section" id="cameras">
          <div class="section-header">
            <div><h3 class="section-title">Camera Health</h3><p class="section-subtitle">Live status across all cameras</p></div>
            <p class="section-subtitle" id="health-summary">● Online: 0 · ● Warning: 0 · ● Offline: 0</p>
          </div>
          <div class="table-wrap">
            <table aria-label="Camera Health">
              <thead><tr><th>Camera ID</th><th>Name</th><th>Location</th><th>Status</th><th>FPS</th><th>Last Frame</th><th>Last Event</th><th>Today</th></tr></thead>
              <tbody id="camera-health-body">__HEALTH_ROWS__</tbody>
            </table>
          </div>
        </section>

        <section class="section" id="events" style="margin-top:16px">
          <div class="section-header">
            <div><h3 class="section-title">Latest Events</h3><p class="section-subtitle">Real-time detection log · Click a row to inspect</p></div>
            <button class="action-button" id="retry-button" type="button" hidden>Retry</button>
          </div>
          <div class="filters">
            <label class="visually-hidden" for="event-search">Search latest events</label>
            <input class="search-field" id="event-search" name="camera_id" value="__CAMERA_ID__" type="search" placeholder="Search, camera, rule, track" aria-label="Search latest events">
            <select class="select-control" id="severity-filter" aria-label="Severity filter"><option value="">All severities</option><option>critical</option><option>high</option><option>medium</option><option>low</option></select>
            <select class="select-control" id="rule-filter" aria-label="Rule filter"><option value="">All rules</option></select>
            <select class="select-control" id="camera-filter" aria-label="Camera filter"><option value="">All cameras</option></select>
          </div>
          <div class="table-wrap">
            <table aria-label="Latest Events">
              <thead><tr><th>Time</th><th>Camera</th><th>Rule</th><th>track_id</th><th>Snapshot</th><th>Severity</th><th>Action</th></tr></thead>
              <tbody id="latest-events-body">__EVENT_ROWS__</tbody>
            </table>
          </div>
          <div class="pagination">
            <button class="action-button" id="prev-page" type="button">Previous</button>
            <span class="muted" id="page-status">Page 1</span>
            <button class="action-button" id="next-page" type="button">Next</button>
          </div>
        </section>
      </main>
    </div>
  </div>

  <aside class="detail-panel" id="detail-panel" aria-label="Event Detail Panel" aria-hidden="true">
    <div class="panel-header">
      <h3>Event Detail</h3>
      <button class="icon-button" id="close-panel" type="button" aria-label="Close event detail">×</button>
    </div>
    <div class="panel-body" id="detail-body"></div>
  </aside>

  <div class="toast-region" id="toast-region" aria-live="polite" aria-atomic="true"></div>
  <script id="dashboard-bootstrap" type="application/json">__BOOTSTRAP_JSON__</script>
  <script>
    (() => {
      "use strict";

      const AUTO_REFRESH_MS = 30000;
      const LOW_FPS_THRESHOLD = 20;
      const PAGE_SIZE = 10;
      const COLORS = ["#ff4048", "#ff7a1a", "#f5c400", "#8b5cf6", "#64748b", "#14b8a6", "#3b82f6"];

      const parseBootstrap = () => JSON.parse(document.getElementById("dashboard-bootstrap").textContent || "{}");
      const bootstrap = parseBootstrap();

      const state = {
        serviceStatus: bootstrap.serviceStatus || "UNKNOWN",
        stats: {
          total_event_count: Number(bootstrap.todayEventCount || 0),
          event_count_by_rule_name: bootstrap.ruleCounts || {},
          event_count_by_camera_id: bootstrap.cameraCounts || {},
          latest_event_timestamp: bootstrap.latestEventTimestamp || null,
        },
        health: Array.isArray(bootstrap.cameraHealth) ? bootstrap.cameraHealth : [],
        events: Array.isArray(bootstrap.latestEvents) ? bootstrap.latestEvents : [],
        filters: { search: "", severity: "", rule: "", camera: bootstrap.cameraId || "" },
        selectedEvent: null,
        page: 1,
        loading: false,
        lastError: null,
      };

      const el = {
        clock: document.getElementById("clock"),
        lastUpdated: document.getElementById("last-updated"),
        refreshButton: document.getElementById("refresh-button"),
        retryButton: document.getElementById("retry-button"),
        globalSearch: document.getElementById("global-search"),
        eventSearch: document.getElementById("event-search"),
        severityFilter: document.getElementById("severity-filter"),
        ruleFilter: document.getElementById("rule-filter"),
        cameraFilter: document.getElementById("camera-filter"),
        ruleDonut: document.getElementById("rule-donut"),
        ruleLegend: document.getElementById("rule-legend"),
        ruleSubtitle: document.getElementById("rule-subtitle"),
        cameraBars: document.getElementById("camera-bars"),
        cameraSubtitle: document.getElementById("camera-subtitle"),
        healthBody: document.getElementById("camera-health-body"),
        healthSummary: document.getElementById("health-summary"),
        eventsBody: document.getElementById("latest-events-body"),
        pageStatus: document.getElementById("page-status"),
        prevPage: document.getElementById("prev-page"),
        nextPage: document.getElementById("next-page"),
        panel: document.getElementById("detail-panel"),
        detailBody: document.getElementById("detail-body"),
        closePanel: document.getElementById("close-panel"),
        toastRegion: document.getElementById("toast-region"),
        navAlertCount: document.getElementById("nav-alert-count"),
      };

      const DashboardServices = {
        async request(path, params = {}) {
          const url = new URL(path, window.location.origin);
          Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== "") {
              url.searchParams.set(key, value);
            }
          });
          const response = await fetch(url, { headers: { "Accept": "application/json" } });
          if (!response.ok) {
            throw new Error(`${response.status} ${response.statusText}`);
          }
          return response.json();
        },
        health() {
          return this.request("/health");
        },
        stats(params) {
          return this.request("/stats", params);
        },
        cameraHealth() {
          return this.request("/cameras/health");
        },
        events(params) {
          return this.request("/events", params);
        },
      };

      const formatNumber = (value) => new Intl.NumberFormat().format(Number(value || 0));
      const normalize = (value) => String(value ?? "").toLowerCase();
      const toTitle = (value) => String(value || "unknown").replace(/[_-]+/g, " ").replace(/\\b\\w/g, (letter) => letter.toUpperCase());
      const eventTime = (event) => {
        const raw = event.created_at || event.timestamp;
        const date = typeof raw === "number" ? new Date(raw * 1000) : new Date(raw);
        return Number.isNaN(date.getTime()) ? String(raw || "") : date.toLocaleTimeString([], { hour12: false });
      };
      const relativeTime = (value) => {
        if (!value) return "—";
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return String(value);
        const seconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000));
        if (seconds < 60) return `${seconds}s ago`;
        if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.round(seconds / 3600)}h ago`;
        return date.toLocaleDateString();
      };
      const getSeverity = (event) => normalize(event.payload?.severity || event.severity || (event.event_type?.includes("danger") ? "critical" : "medium"));
      const getRule = (event) => String(event.event_type || event.payload?.rule_name || "unknown");
      const getCamera = (event) => String(event.camera_id || "unknown");
      const snapshotUrl = (snapshotPath) => {
        if (!snapshotPath) return "";
        const clean = String(snapshotPath).replace(/^.*data\\/snapshots\\//, "").replace(/^\\/+/, "");
        return `/snapshots/${clean.split("/").map(encodeURIComponent).join("/")}`;
      };
      const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      })[char]);

      const animateTextNumber = (node, nextValue) => {
        if (!node) return;
        const current = Number(node.dataset.number || node.textContent.replace(/[^0-9.-]/g, "") || 0);
        const next = Number(nextValue || 0);
        node.dataset.number = String(next);
        if (!Number.isFinite(current) || !Number.isFinite(next) || node.textContent.includes("/")) {
          node.textContent = formatNumber(next);
          return;
        }
        const start = performance.now();
        const duration = 520;
        const tick = (now) => {
          const progress = Math.min(1, (now - start) / duration);
          const eased = 1 - Math.pow(1 - progress, 3);
          node.textContent = formatNumber(Math.round(current + (next - current) * eased));
          if (progress < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      };

      const filteredEvents = () => {
        const search = normalize(state.filters.search);
        return state.events
          .filter((event) => !state.filters.severity || getSeverity(event) === state.filters.severity)
          .filter((event) => !state.filters.rule || getRule(event) === state.filters.rule)
          .filter((event) => !state.filters.camera || getCamera(event) === state.filters.camera)
          .filter((event) => {
            if (!search) return true;
            return [event.id, event.track_id, getCamera(event), getRule(event), event.payload?.message, JSON.stringify(event.payload || {})]
              .some((value) => normalize(value).includes(search));
          })
          .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
      };

      const DashboardComponents = {
        renderSummary() {
          const healthRows = state.health.map((row) => normalizeHealth(row));
          const activeCameras = healthRows.length || Object.keys(state.stats.event_count_by_camera_id || {}).length;
          const online = healthRows.filter((row) => row.status === "online").length;
          const warning = healthRows.filter((row) => row.status === "warning").length;
          const offline = healthRows.filter((row) => row.status === "offline").length;
          const critical = state.events.filter((event) => getSeverity(event) === "critical").length;
          const high = state.events.filter((event) => getSeverity(event) === "high").length;
          animateTextNumber(document.querySelector("[data-kpi='todayEvents']"), state.stats.total_event_count);
          animateTextNumber(document.querySelector("[data-kpi='activeAlerts']"), critical + high);
          document.querySelector("[data-kpi='activeCameras']").textContent = formatNumber(activeCameras);
          document.querySelector("[data-kpi='onlineCameras']").textContent = `${formatNumber(online || activeCameras)} / ${formatNumber(activeCameras)}`;
          document.querySelector("[data-kpi-sub='activeAlerts']").textContent = `${formatNumber(critical)} Critical · ${formatNumber(high)} High`;
          document.querySelector("[data-kpi-sub='activeCameras']").textContent = `${formatNumber(warning + offline)} degraded · 0 new`;
          document.querySelector("[data-kpi-sub='onlineCameras']").textContent = `${formatNumber(offline)} offline · ${formatNumber(warning)} warning`;
          el.navAlertCount.textContent = formatNumber(critical + high);
        },
        renderRuleChart() {
          const counts = state.stats.event_count_by_rule_name || {};
          const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
          const total = entries.reduce((sum, [, count]) => sum + Number(count), 0);
          el.ruleSubtitle.textContent = `Today · ${formatNumber(total)} total detections`;
          if (!entries.length) {
            el.ruleDonut.style.background = "conic-gradient(var(--border) 0deg 360deg)";
            el.ruleLegend.innerHTML = emptyState("No rule events yet.");
            return;
          }
          let cursor = 0;
          const segments = entries.map(([name, count], index) => {
            const degrees = total ? (Number(count) / total) * 360 : 0;
            const segment = `${COLORS[index % COLORS.length]} ${cursor}deg ${cursor + degrees}deg`;
            cursor += degrees;
            return segment;
          });
          el.ruleDonut.style.background = `conic-gradient(${segments.join(", ")})`;
          el.ruleLegend.innerHTML = entries.map(([name, count], index) => {
            const percent = total ? Math.round((Number(count) / total) * 100) : 0;
            const active = state.filters.rule === name ? "active" : "";
            return `<button class="${active}" type="button" data-rule="${escapeHtml(name)}" aria-label="Filter by ${escapeHtml(name)}">
              <span class="legend-dot" style="background:${COLORS[index % COLORS.length]}"></span>
              <span>${escapeHtml(toTitle(name))}</span><strong>${formatNumber(count)}</strong><span>${percent}%</span>
            </button>`;
          }).join("");
        },
        renderCameraChart() {
          const counts = state.stats.event_count_by_camera_id || {};
          const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
          const max = Math.max(1, ...entries.map(([, count]) => Number(count)));
          el.cameraSubtitle.textContent = `Today · ${state.filters.camera || "all"} cameras`;
          if (!entries.length) {
            el.cameraBars.innerHTML = emptyState("No camera events yet.");
            return;
          }
          el.cameraBars.innerHTML = entries.map(([camera, count]) => {
            const width = Math.max(4, (Number(count) / max) * 100);
            const active = state.filters.camera === camera ? "active" : "";
            return `<span class="bar-label">${escapeHtml(camera)}</span>
              <div class="bar-track"><button class="bar ${active}" type="button" data-camera="${escapeHtml(camera)}" style="width:${width}%" aria-label="Filter by ${escapeHtml(camera)}"></button></div>
              <span class="bar-value">${formatNumber(count)}</span>`;
          }).join("");
        },
        renderHealth() {
          const rows = state.health.map((row) => normalizeHealth(row));
          const online = rows.filter((row) => row.status === "online").length;
          const warning = rows.filter((row) => row.status === "warning").length;
          const offline = rows.filter((row) => row.status === "offline").length;
          el.healthSummary.innerHTML = `<span style="color:var(--success)">●</span> Online: ${online} · <span style="color:var(--warning)">●</span> Warning: ${warning} · <span style="color:var(--danger)">●</span> Offline: ${offline}`;
          if (!rows.length) {
            el.healthBody.innerHTML = `<tr><td colspan="8">${emptyState("No runtime camera health reported yet.")}</td></tr>`;
            return;
          }
          const todayCounts = state.stats.event_count_by_camera_id || {};
          el.healthBody.innerHTML = rows.map((row) => `<tr>
            <td class="mono">${escapeHtml(row.camera_id)}</td>
            <td>${escapeHtml(row.name)}</td>
            <td class="muted">${escapeHtml(row.location)}</td>
            <td><span class="status-badge ${row.status}"><span>●</span>${escapeHtml(toTitle(row.status))}</span></td>
            <td class="mono" style="color:${row.status === "warning" ? "var(--warning)" : "inherit"}">${row.fps ? `${row.fps} fps` : "—"}</td>
            <td class="muted">${escapeHtml(relativeTime(row.last_frame_at))}</td>
            <td class="muted">${escapeHtml(relativeTime(row.last_event_at))}</td>
            <td>${formatNumber(todayCounts[row.camera_id] || row.emitted_event_count || 0)}</td>
          </tr>`).join("");
        },
        renderEvents() {
          syncFilterOptions();
          const events = filteredEvents();
          const totalPages = Math.max(1, Math.ceil(events.length / PAGE_SIZE));
          state.page = Math.min(state.page, totalPages);
          const pageEvents = events.slice((state.page - 1) * PAGE_SIZE, state.page * PAGE_SIZE);
          if (!pageEvents.length) {
            el.eventsBody.innerHTML = `<tr><td colspan="7">${emptyState("No events match the current filters.")}</td></tr>`;
          } else {
            el.eventsBody.innerHTML = pageEvents.map((event) => eventRow(event)).join("");
          }
          el.pageStatus.textContent = `Page ${state.page} / ${totalPages} · ${formatNumber(events.length)} events`;
          el.prevPage.disabled = state.page <= 1;
          el.nextPage.disabled = state.page >= totalPages;
        },
      };

      const normalizeHealth = (row) => {
        const source = String(row.source || "");
        const fps = Number(row.fps || row.payload?.fps || (row.status === "offline" ? 0 : 30));
        const baseStatus = normalize(row.status || "unknown");
        const status = baseStatus === "offline" ? "offline" : fps > 0 && fps < LOW_FPS_THRESHOLD ? "warning" : baseStatus === "unknown" ? "warning" : baseStatus;
        const cameraId = String(row.camera_id || row.id || "unknown");
        return {
          ...row,
          camera_id: cameraId,
          name: row.name || toTitle(cameraId),
          location: row.location || source.split("/").pop() || "—",
          status,
          fps,
        };
      };

      const emptyState = (message) => `<div class="empty"><div class="empty-illustration" aria-hidden="true">∅</div>${escapeHtml(message)}</div>`;

      const eventRow = (event) => {
        const severity = getSeverity(event);
        const url = snapshotUrl(event.snapshot_path);
        const snapshot = url
          ? `<a class="snapshot-link" href="${url}" target="_blank" rel="noopener noreferrer"><img class="snapshot-thumb" src="${url}" alt="Event snapshot"></a>`
          : `<span class="muted">Missing</span>`;
        return `<tr tabindex="0" data-event-id="${escapeHtml(event.id)}">
          <td class="mono">${escapeHtml(eventTime(event))}</td>
          <td><span class="mono">${escapeHtml(getCamera(event))}</span></td>
          <td>${escapeHtml(toTitle(getRule(event)))}</td>
          <td class="mono">${escapeHtml(event.track_id ?? "—")}</td>
          <td>${snapshot}</td>
          <td><span class="severity-badge ${severity}">${escapeHtml(toTitle(severity))}</span></td>
          <td><button class="action-button" type="button" data-view-event="${escapeHtml(event.id)}">View</button></td>
        </tr>`;
      };

      const renderAll = () => {
        DashboardComponents.renderSummary();
        DashboardComponents.renderRuleChart();
        DashboardComponents.renderCameraChart();
        DashboardComponents.renderHealth();
        DashboardComponents.renderEvents();
      };

      const syncFilterOptions = () => {
        const rules = [...new Set(state.events.map(getRule))].sort();
        const cameras = [...new Set(state.events.map(getCamera))].sort();
        setOptions(el.ruleFilter, "All rules", rules, state.filters.rule);
        setOptions(el.cameraFilter, "All cameras", cameras, state.filters.camera);
      };

      const setOptions = (select, label, values, selected) => {
        const current = select.value || selected || "";
        select.innerHTML = `<option value="">${label}</option>` + values.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("");
        select.value = values.includes(current) ? current : "";
      };

      const loadDashboard = async ({ silent = false } = {}) => {
        try {
          state.loading = true;
          state.lastError = null;
          el.retryButton.hidden = true;
          if (!silent) showToast("Refreshing dashboard...");
          const todayStart = new Date();
          todayStart.setHours(0, 0, 0, 0);
          const params = { start_at: todayStart.toISOString(), camera_id: state.filters.camera };
          const [status, stats, health, events] = await Promise.all([
            DashboardServices.health(),
            DashboardServices.stats(params),
            DashboardServices.cameraHealth(),
            DashboardServices.events({ limit: 500, camera_id: state.filters.camera }),
          ]);
          state.serviceStatus = status.status || "ok";
          state.stats = stats;
          state.health = Array.isArray(health) ? health : [];
          state.events = Array.isArray(events) ? events : [];
          el.lastUpdated.textContent = `Last updated just now · Auto-refresh every 30 s`;
          renderAll();
          if (!silent) showToast("Dashboard updated.");
        } catch (error) {
          state.lastError = error;
          el.retryButton.hidden = false;
          showToast(`Unable to refresh dashboard: ${error.message}`);
        } finally {
          state.loading = false;
        }
      };

      const openPanel = (event) => {
        state.selectedEvent = event;
        const url = snapshotUrl(event.snapshot_path);
        const metadata = event.payload?.metadata || event.payload || {};
        el.detailBody.innerHTML = `
          ${url ? `<img class="panel-image" src="${url}" alt="Selected event snapshot">` : `<div class="panel-image empty">No snapshot</div>`}
          <dl class="detail-list">
            <dt>Event ID</dt><dd class="mono">${escapeHtml(event.id)}</dd>
            <dt>Track ID</dt><dd class="mono">${escapeHtml(event.track_id ?? "—")}</dd>
            <dt>Camera</dt><dd>${escapeHtml(getCamera(event))}</dd>
            <dt>Rule</dt><dd>${escapeHtml(toTitle(getRule(event)))}</dd>
            <dt>Timestamp</dt><dd>${escapeHtml(event.created_at || event.timestamp || "—")}</dd>
            <dt>Confidence</dt><dd>${escapeHtml(event.payload?.confidence ?? event.confidence ?? "—")}</dd>
            <dt>Duration</dt><dd>${escapeHtml(event.payload?.duration ?? "—")}</dd>
            <dt>Bounding Box</dt><dd class="mono">${escapeHtml(JSON.stringify(event.payload?.bbox || event.payload?.bounding_box || "—"))}</dd>
          </dl>
          <h4>Metadata</h4>
          <pre class="json-box">${escapeHtml(JSON.stringify(metadata, null, 2))}</pre>
          <div class="panel-actions">
            ${url ? `<a class="action-button" href="${url}" target="_blank" rel="noopener noreferrer">Open Snapshot</a><a class="action-button" href="${url}" download>Download Snapshot</a>` : ""}
            <button class="action-button" type="button" id="copy-json">Copy Event JSON</button>
          </div>`;
        el.panel.classList.add("open");
        el.panel.setAttribute("aria-hidden", "false");
        el.closePanel.focus();
      };

      const closePanel = () => {
        el.panel.classList.remove("open");
        el.panel.setAttribute("aria-hidden", "true");
      };

      const showToast = (message) => {
        const toast = document.createElement("div");
        toast.className = "toast";
        toast.textContent = message;
        el.toastRegion.appendChild(toast);
        window.setTimeout(() => toast.remove(), 3200);
      };

      const updateClock = () => {
        el.clock.textContent = new Date().toLocaleTimeString([], { hour12: false });
      };

      const handleFilterChange = () => {
        state.filters.search = el.eventSearch.value || el.globalSearch.value || "";
        state.filters.severity = el.severityFilter.value;
        state.filters.rule = el.ruleFilter.value;
        state.filters.camera = el.cameraFilter.value;
        state.page = 1;
        renderAll();
      };

      el.refreshButton.addEventListener("click", () => loadDashboard());
      el.retryButton.addEventListener("click", () => loadDashboard());
      el.globalSearch.addEventListener("input", () => { el.eventSearch.value = el.globalSearch.value; handleFilterChange(); });
      el.eventSearch.addEventListener("input", handleFilterChange);
      el.severityFilter.addEventListener("change", handleFilterChange);
      el.ruleFilter.addEventListener("change", handleFilterChange);
      el.cameraFilter.addEventListener("change", () => {
        state.filters.camera = el.cameraFilter.value;
        state.page = 1;
        loadDashboard({ silent: true });
      });
      el.prevPage.addEventListener("click", () => { state.page = Math.max(1, state.page - 1); DashboardComponents.renderEvents(); });
      el.nextPage.addEventListener("click", () => { state.page += 1; DashboardComponents.renderEvents(); });
      el.ruleLegend.addEventListener("click", (event) => {
        const button = event.target.closest("[data-rule]");
        if (!button) return;
        state.filters.rule = state.filters.rule === button.dataset.rule ? "" : button.dataset.rule;
        state.page = 1;
        renderAll();
      });
      el.cameraBars.addEventListener("click", (event) => {
        const button = event.target.closest("[data-camera]");
        if (!button) return;
        state.filters.camera = state.filters.camera === button.dataset.camera ? "" : button.dataset.camera;
        state.page = 1;
        loadDashboard({ silent: true });
      });
      el.eventsBody.addEventListener("click", (event) => {
        const trigger = event.target.closest("[data-view-event], tr[data-event-id]");
        if (!trigger) return;
        const id = Number(trigger.dataset.viewEvent || trigger.dataset.eventId);
        const selected = state.events.find((item) => Number(item.id) === id);
        if (selected) openPanel(selected);
      });
      el.eventsBody.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        const row = event.target.closest("tr[data-event-id]");
        if (!row) return;
        event.preventDefault();
        const selected = state.events.find((item) => Number(item.id) === Number(row.dataset.eventId));
        if (selected) openPanel(selected);
      });
      el.closePanel.addEventListener("click", closePanel);
      document.addEventListener("click", (event) => {
        if (event.target.id === "copy-json" && state.selectedEvent) {
          navigator.clipboard.writeText(JSON.stringify(state.selectedEvent, null, 2));
          showToast("Event JSON copied.");
        }
      });
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closePanel();
      });

      updateClock();
      window.setInterval(updateClock, 1000);
      renderAll();
      loadDashboard({ silent: true });
      window.setInterval(() => loadDashboard({ silent: true }), AUTO_REFRESH_MS);
    })();
  </script>
</body>
</html>"""


def _render_count_rows(counts: dict[str, int], label: str) -> str:
    if not counts:
        return '<p class="empty">No saved events yet.</p>'

    rows = []
    for name, count in counts.items():
        if label == "camera_id":
            rows.append(
                '<span class="bar-label">{name}</span>'
                '<div class="bar-track"><button class="bar" type="button" '
                'data-camera="{name}" style="width:100%" aria-label="Filter by {name}">'
                '</button></div><span class="bar-value">{count}</span>'.format(
                    name=_html(name),
                    count=count,
                )
            )
        else:
            rows.append(
                '<button type="button" data-rule="{name}">'
                '<span class="legend-dot"></span><span>{name}</span>'
                '<strong>{count}</strong><span></span></button>'.format(
                    name=_html(name),
                    count=count,
                )
            )
    return "\n".join(rows)


def _render_camera_health_rows(camera_health_rows: list[dict]) -> str:
    if not camera_health_rows:
        return '<tr><td colspan="8"><p class="empty">No runtime camera health reported yet.</p></td></tr>'

    rows = []
    for row in camera_health_rows:
        camera_id = _html(row.get("camera_id") or "")
        source = str(row.get("source") or "")
        status = _html(row.get("status") or "unknown")
        rows.append(
            f"""<tr>
      <td class="mono">{camera_id}</td>
      <td>{camera_id}</td>
      <td class="muted">{_html(Path(source).name or "—")}</td>
      <td><span class="status-badge {status}">● {_html(status.title())}</span></td>
      <td class="mono">—</td>
      <td class="muted">{_html(row.get("last_frame_at") or "—")}</td>
      <td class="muted">{_html(row.get("last_event_at") or "—")}</td>
      <td>{row.get("emitted_event_count", 0)}</td>
    </tr>"""
        )
    return "\n".join(rows)


def _render_latest_event_rows(events: list[dict]) -> str:
    if not events:
        return '<tr><td colspan="7"><p class="empty">No latest events to show.</p></td></tr>'

    rows = []
    for event in events:
        snapshot_path = event.get("snapshot_path")
        rows.append(
            f"""<tr tabindex="0" data-event-id="{event["id"]}">
      <td class="mono">{_html(event.get("created_at") or event.get("timestamp") or "")}</td>
      <td class="mono">{_html(event.get("camera_id") or "")}</td>
      <td>{_html(event.get("event_type") or "")}</td>
      <td>{event.get("track_id")}</td>
      <td>{_render_snapshot_cell(snapshot_path)}</td>
      <td><span class="severity-badge medium">Medium</span></td>
      <td><button class="action-button" type="button" data-view-event="{event["id"]}">View</button></td>
    </tr>"""
        )
    return "\n".join(rows)


def _render_snapshot_cell(snapshot_path: object) -> str:
    if not snapshot_path:
        return '<span class="muted">Missing</span>'

    snapshot_url = _snapshot_url(snapshot_path)
    if snapshot_url is None:
        return '<span class="muted">Missing</span>'

    escaped_url = _html(snapshot_url)
    return (
        f'<a class="snapshot-link" href="{escaped_url}" target="_blank" '
        f'rel="noopener noreferrer">'
        f'<img class="snapshot-thumb" src="{escaped_url}" alt="Event snapshot">'
        "</a>"
    )


def _snapshot_url(snapshot_path: object) -> str | None:
    path = str(snapshot_path)
    if not path:
        return None
    snapshot_dir = Path(os.environ.get("SNAPSHOT_DIR", "data/snapshots"))
    try:
        path = Path(path).relative_to(snapshot_dir).as_posix()
    except ValueError:
        pass
    marker = "data/snapshots/"
    if marker in path:
        path = path.split(marker, 1)[1]
    path = path.lstrip("/")
    return "/snapshots/" + "/".join(quote(part) for part in Path(path).parts)


def _json_script(value: object) -> str:
    return (
        json.dumps(value, sort_keys=True)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


def _html(value: object) -> str:
    return escape(str(value))
