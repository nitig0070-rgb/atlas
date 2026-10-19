<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Project Atlas — Market Research Copilot</title>
  <style>
    :root {
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --bg-page: #f1f5f9;
      --bg-surface: #ffffff;
      --bg-header: #0f172a;
      --border-subtle: #e2e8f0;
      --border-focus: #3b82f6;
      --text-heading: #0f172a;
      --text-body: #334155;
      --text-muted: #64748b;
      --primary: #2563eb;
      --primary-hover: #1d4ed8;
      --primary-light: #eff6ff;
      --primary-border: #bfdbfe;
      --success: #059669;
      --success-light: #ecfdf5;
      --success-border: #a7f3d0;
      --warning: #d97706;
      --warning-light: #fffbeb;
      --warning-border: #fde68a;
      --danger: #dc2626;
      --danger-light: #fef2f2;
      --danger-border: #fecaca;
      --radius-sm: 6px;
      --radius-md: 10px;
      --radius-lg: 16px;
      --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
      --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
      --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.03);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    
    html, body {
      height: 100%;
      overflow: hidden; /* Screen itself never scrolls */
    }

    body {
      font-family: var(--font-sans);
      background: var(--bg-page);
      color: var(--text-body);
      display: flex;
      flex-direction: column;
      line-height: 1.5;
    }

    /* Header */
    header.app-header {
      background: var(--bg-header);
      color: #ffffff;
      padding: 0.75rem 1.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
      flex-shrink: 0;
      z-index: 50;
      height: 56px;
    }
    .header-brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      text-decoration: none;
      color: white;
    }
    .brand-icon {
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, #3b82f6, #06b6d4);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 1.1rem;
      box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .brand-title {
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .brand-badge {
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      background: rgba(255, 255, 255, 0.15);
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      color: #93c5fd;
    }
    .header-right {
      display: flex;
      align-items: center;
      gap: 0.85rem;
    }
    .status-indicator {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.8rem;
      color: #94a3b8;
      background: rgba(255, 255, 255, 0.08);
      padding: 0.3rem 0.7rem;
      border-radius: 9999px;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      background: #10b981;
      border-radius: 50%;
      box-shadow: 0 0 6px #10b981;
    }
    .client-selector-form {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(255, 255, 255, 0.1);
      padding: 0.25rem 0.6rem 0.25rem 0.75rem;
      border-radius: 8px;
      border: 1px solid rgba(255, 255, 255, 0.15);
    }
    .client-selector-form label {
      font-size: 0.78rem;
      color: #cbd5e1;
      font-weight: 500;
    }
    .client-selector-form select {
      background: #1e293b;
      color: #ffffff;
      border: 1px solid #475569;
      border-radius: 6px;
      padding: 0.35rem 0.6rem;
      font-size: 0.82rem;
      font-weight: 500;
      cursor: pointer;
      outline: none;
    }
    .btn-new-chat {
      background: rgba(255, 255, 255, 0.12);
      color: #ffffff;
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: 6px;
      padding: 0.35rem 0.75rem;
      font-size: 0.82rem;
      font-weight: 500;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      transition: background 0.15s;
    }
    .btn-new-chat:hover {
      background: rgba(255, 255, 255, 0.22);
    }

    /* Main Container (Fixed Viewport Height) */
    .app-main {
      flex: 1;
      max-width: 1400px;
      width: 100%;
      margin: 0 auto;
      padding: 1rem 1.25rem;
      display: grid;
      grid-template-columns: 310px 1fr;
      gap: 1.25rem;
      min-height: 0; /* Crucial for inner scroll */
      height: calc(100vh - 56px);
      box-sizing: border-box;
    }
    @media (max-width: 900px) {
      .app-main {
        grid-template-columns: 1fr;
        height: auto;
        overflow-y: auto;
      }
    }

    /* Sidebar (Scrolls independently if needed) */
    .sidebar {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      overflow-y: auto;
      min-height: 0;
      padding-right: 0.25rem;
    }
    .sidebar::-webkit-scrollbar {
      width: 5px;
    }
    .sidebar::-webkit-scrollbar-thumb {
      background: #cbd5e1;
      border-radius: 4px;
    }
    .side-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      padding: 1.15rem;
      box-shadow: var(--shadow-sm);
    }
    .side-card-title {
      font-size: 0.82rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      margin-bottom: 0.65rem;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }
    .client-profile-box {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: var(--radius-md);
      padding: 0.75rem;
    }
    .client-name {
      font-weight: 700;
      font-size: 0.95rem;
      color: var(--text-heading);
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }
    .client-id-pill {
      background: #e2e8f0;
      color: #334155;
      font-size: 0.75rem;
      padding: 0.1rem 0.4rem;
      border-radius: 4px;
      font-family: monospace;
      font-weight: 600;
    }
    .client-meta {
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: 0.35rem;
      line-height: 1.4;
    }
    .client-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 0.35rem;
      margin-top: 0.45rem;
    }
    .tag {
      font-size: 0.7rem;
      font-weight: 600;
      padding: 0.12rem 0.4rem;
      border-radius: 4px;
      background: #e0f2fe;
      color: #0369a1;
    }

    /* Quick Prompts */
    .prompts-list {
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
    }
    .prompt-chip {
      background: #f8fafc;
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 0.55rem 0.75rem;
      font-size: 0.8rem;
      color: var(--text-body);
      cursor: pointer;
      text-align: left;
      transition: all 0.15s ease;
      line-height: 1.35;
      display: flex;
      align-items: flex-start;
      gap: 0.4rem;
    }
    .prompt-chip:hover {
      background: var(--primary-light);
      border-color: var(--primary-border);
      color: var(--primary);
      transform: translateY(-1px);
      box-shadow: var(--shadow-sm);
    }
    .prompt-chip::before {
      content: "💬";
      font-size: 0.8rem;
    }

    /* Chat Section */
    .chat-section {
      display: flex;
      flex-direction: column;
      height: 100%;
      min-height: 0;
      overflow: hidden;
    }
    .chat-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      height: 100%;
      min-height: 0;
      overflow: hidden;
      position: relative;
    }

    /* Inner Chat Scroll Area (Only this content scrolls) */
    .chat-scroll-area {
      flex: 1;
      overflow-y: auto;
      padding: 1.25rem 1.5rem 1rem 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
      min-height: 0;
    }
    .chat-scroll-area::-webkit-scrollbar {
      width: 6px;
    }
    .chat-scroll-area::-webkit-scrollbar-thumb {
      background: #cbd5e1;
      border-radius: 4px;
    }
    .chat-scroll-area::-webkit-scrollbar-thumb:hover {
      background: #94a3b8;
    }

    /* History Thread */
    .thread-container {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }
    .message-row {
      display: flex;
      gap: 0.85rem;
      align-items: flex-start;
    }
    .message-row.user {
      flex-direction: row-reverse;
    }
    .avatar {
      width: 34px;
      height: 34px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.95rem;
      flex-shrink: 0;
      box-shadow: var(--shadow-sm);
    }
    .avatar.user-avatar {
      background: linear-gradient(135deg, #6366f1, #4f46e5);
      color: white;
    }
    .avatar.ai-avatar {
      background: linear-gradient(135deg, #2563eb, #0284c7);
      color: white;
    }
    .bubble {
      max-width: 82%;
      padding: 0.85rem 1.15rem;
      border-radius: 14px;
      font-size: 0.92rem;
      line-height: 1.55;
      position: relative;
    }
    .message-row.user .bubble {
      background: #2563eb;
      color: #ffffff;
      border-bottom-right-radius: 3px;
      box-shadow: 0 2px 4px rgba(37, 99, 235, 0.18);
    }
    .message-row.assistant .bubble {
      background: #f8fafc;
      color: var(--text-heading);
      border: 1px solid #e2e8f0;
      border-bottom-left-radius: 3px;
      box-shadow: var(--shadow-sm);
    }
    .bubble-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.35rem;
      font-size: 0.75rem;
    }
    .message-row.user .bubble-header {
      color: #bfdbfe;
    }
    .message-row.assistant .bubble-header {
      color: var(--text-muted);
      font-weight: 600;
    }
    .bubble-content {
      white-space: pre-wrap;
      word-break: break-word;
    }
    .bubble-actions {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-top: 0.5rem;
      padding-top: 0.4rem;
      border-top: 1px solid rgba(0, 0, 0, 0.06);
    }
    .btn-copy {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 0.72rem;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      padding: 0.2rem 0.4rem;
      border-radius: 4px;
      transition: background 0.15s;
    }
    .btn-copy:hover {
      background: #e2e8f0;
      color: var(--text-heading);
    }

    /* Empty state */
    .empty-state {
      text-align: center;
      padding: 3rem 1rem;
      color: var(--text-muted);
    }
    .empty-icon {
      font-size: 2.5rem;
      margin-bottom: 0.75rem;
    }
    .empty-title {
      font-size: 1.15rem;
      font-weight: 700;
      color: var(--text-heading);
      margin-bottom: 0.4rem;
    }
    .empty-desc {
      font-size: 0.88rem;
      max-width: 480px;
      margin: 0 auto 1.5rem auto;
      line-height: 1.5;
    }

    /* Prominent Answer Card */
    .answer-card {
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-left: 4px solid var(--primary);
      border-radius: var(--radius-lg);
      padding: 1.15rem 1.25rem;
      box-shadow: var(--shadow-sm);
    }
    .answer-card-header {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      font-size: 0.88rem;
      font-weight: 700;
      color: var(--text-heading);
      margin-bottom: 0.65rem;
    }
    .answer-card-body {
      font-size: 0.95rem;
      line-height: 1.6;
      color: var(--text-heading);
      white-space: pre-wrap;
      word-break: break-word;
      background: #f8fafc;
      padding: 0.9rem 1rem;
      border-radius: var(--radius-md);
      border: 1px solid #e2e8f0;
    }

    /* Service / Rate Limit Notice Banner */
    .notice-card {
      background: var(--warning-light);
      border: 1px solid var(--warning-border);
      border-left: 4px solid var(--warning);
      border-radius: var(--radius-lg);
      padding: 1.15rem 1.25rem;
      box-shadow: var(--shadow-sm);
    }
    .notice-card-header {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.9rem;
      font-weight: 700;
      color: #92400e;
      margin-bottom: 0.35rem;
    }
    .notice-card-body {
      font-size: 0.9rem;
      color: #78350f;
      line-height: 1.5;
    }
    .notice-card-help {
      font-size: 0.78rem;
      color: #a16207;
      margin-top: 0.5rem;
      padding-top: 0.4rem;
      border-top: 1px dashed rgba(217, 119, 6, 0.3);
    }

    /* Result Metadata Inspector Card */
    .result-inspector {
      background: #ffffff;
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      padding: 1.15rem 1.25rem;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
    }
    .inspector-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 0.75rem;
      padding-bottom: 0.65rem;
      border-bottom: 1px solid var(--border-subtle);
    }
    .confidence-meter {
      display: flex;
      align-items: center;
      gap: 0.65rem;
    }
    .confidence-label {
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--text-muted);
    }
    .confidence-track {
      width: 100px;
      height: 8px;
      background: #e2e8f0;
      border-radius: 9999px;
      overflow: hidden;
    }
    .confidence-bar {
      height: 100%;
      border-radius: 9999px;
      transition: width 0.4s ease;
    }
    .confidence-bar.high { background: var(--success); }
    .confidence-bar.medium { background: var(--warning); }
    .confidence-bar.low { background: var(--danger); }
    .confidence-val {
      font-size: 0.82rem;
      font-weight: 700;
      font-family: monospace;
    }

    .escalation-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.2rem 0.6rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
    }
    .escalation-badge.verified {
      background: var(--success-light);
      color: var(--success);
      border: 1px solid var(--success-border);
    }
    .escalation-badge.escalated {
      background: var(--warning-light);
      color: var(--warning);
      border: 1px solid var(--warning-border);
    }

    /* Citations List */
    .citations-section h4, .conflicts-section h4, .derived-section h4 {
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      margin-bottom: 0.45rem;
      display: flex;
      align-items: center;
      gap: 0.35rem;
    }
    .citation-cards {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 0.6rem;
    }
    .citation-card {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: var(--radius-md);
      padding: 0.6rem 0.8rem;
      font-size: 0.8rem;
      transition: border-color 0.15s;
    }
    .citation-card:hover {
      border-color: #cbd5e1;
    }
    .citation-pills {
      display: flex;
      align-items: center;
      gap: 0.35rem;
      margin-bottom: 0.25rem;
    }
    .report-id-pill {
      background: #2563eb;
      color: white;
      font-weight: 700;
      font-size: 0.7rem;
      padding: 0.1rem 0.4rem;
      border-radius: 4px;
      font-family: monospace;
    }
    .page-pill {
      background: #e2e8f0;
      color: #334155;
      font-weight: 600;
      font-size: 0.7rem;
      padding: 0.1rem 0.4rem;
      border-radius: 4px;
    }
    .citation-title {
      font-weight: 600;
      color: var(--text-heading);
      line-height: 1.35;
    }
    .citation-snippet {
      font-size: 0.72rem;
      color: var(--text-muted);
      margin-top: 0.3rem;
      font-style: italic;
      line-height: 1.3;
    }

    /* Conflicts Callout */
    .conflict-callout {
      background: var(--warning-light);
      border: 1px solid var(--warning-border);
      border-radius: var(--radius-md);
      padding: 0.65rem 0.85rem;
      font-size: 0.82rem;
      color: #92400e;
      display: flex;
      gap: 0.5rem;
      align-items: flex-start;
    }
    .conflict-callout ul {
      margin-left: 1.2rem;
      margin-top: 0.25rem;
    }

    /* Derived Values Chips */
    .derived-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 0.45rem;
    }
    .derived-chip {
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      border-radius: var(--radius-sm);
      padding: 0.3rem 0.6rem;
      font-size: 0.75rem;
      font-family: monospace;
      color: #1e293b;
    }

    /* Feedback Controls */
    .feedback-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-top: 0.5rem;
      border-top: 1px solid var(--border-subtle);
      font-size: 0.8rem;
      color: var(--text-muted);
    }
    .feedback-buttons {
      display: flex;
      gap: 0.4rem;
    }
    .btn-rating {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      padding: 0.22rem 0.55rem;
      cursor: pointer;
      font-size: 0.9rem;
      transition: all 0.15s ease;
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
    }
    .btn-rating:hover {
      background: #e2e8f0;
      transform: translateY(-1px);
    }
    .btn-rating.up:hover {
      border-color: var(--success);
      background: var(--success-light);
    }
    .btn-rating.down:hover {
      border-color: var(--danger);
      background: var(--danger-light);
    }

    /* Fixed Bottom Composer Container */
    .composer-container {
      flex-shrink: 0;
      padding: 0.75rem 1.5rem 1rem 1.5rem;
      background: #ffffff;
      border-top: 1px solid var(--border-subtle);
      box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.03);
      position: relative;
    }
    .composer-wrapper {
      background: #f8fafc;
      border: 2px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      padding: 0.65rem 0.9rem;
      transition: border-color 0.2s, box-shadow 0.2s, background-color 0.2s;
    }
    .composer-wrapper:focus-within {
      background: #ffffff;
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
    }
    .composer-textarea {
      width: 100%;
      border: none;
      outline: none;
      background: transparent;
      font-family: inherit;
      font-size: 0.92rem;
      line-height: 1.45;
      resize: none;
      min-height: 48px;
      max-height: 140px;
      color: var(--text-heading);
    }
    .composer-textarea::placeholder {
      color: #94a3b8;
    }
    .composer-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 0.35rem;
      padding-top: 0.35rem;
      border-top: 1px solid #e2e8f0;
    }
    .char-count {
      font-size: 0.72rem;
      color: var(--text-muted);
    }
    .composer-actions {
      display: flex;
      align-items: center;
      gap: 0.6rem;
    }
    .btn-submit {
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      color: #ffffff;
      border: none;
      border-radius: 7px;
      padding: 0.45rem 1.1rem;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
      transition: all 0.15s ease;
    }
    .btn-submit:hover {
      background: linear-gradient(135deg, #1d4ed8, #1e40af);
      transform: translateY(-1px);
      box-shadow: 0 4px 6px rgba(37, 99, 235, 0.25);
    }
    .btn-submit:active {
      transform: translateY(0);
    }
    .btn-submit:disabled {
      background: #94a3b8;
      cursor: not-allowed;
      transform: none;
      box-shadow: none;
    }

    /* Loading Overlay */
    .loading-overlay {
      display: none;
      align-items: center;
      justify-content: center;
      gap: 0.6rem;
      background: rgba(255, 255, 255, 0.95);
      border-radius: var(--radius-md);
      padding: 0.65rem 1rem;
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--primary);
      margin-bottom: 0.5rem;
      border: 1px dashed var(--primary-border);
    }
    .spinner {
      width: 16px;
      height: 16px;
      border: 2px solid #bfdbfe;
      border-top-color: var(--primary);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  </style>
</head>
<body>

  <!-- App Header (Fixed at top) -->
  <header class="app-header">
    <div class="header-brand">
      <div class="brand-icon">A</div>
      <div>
        <div class="brand-title">
          Project Atlas
          <span class="brand-badge">Report Copilot</span>
        </div>
      </div>
    </div>

    <div class="header-right">
      <div class="status-indicator">
        <span class="status-dot"></span>
        <span>AI Engine Ready</span>
      </div>

      <!-- Demo Client Switcher -->
      <form class="client-selector-form" method="get" action="/copilot">
        <label for="demo_client">Client</label>
        <select id="demo_client" name="demo_client" onchange="this.form.submit()">
          <option value="C-01" <?= $client_id==='C-01'?'selected':'' ?>>Northwind Utilities (C-01)</option>
          <option value="C-02" <?= $client_id==='C-02'?'selected':'' ?>>Blue Delta Infra (C-02)</option>
        </select>
      </form>

      <a href="/copilot/reset" class="btn-new-chat" title="Start a fresh conversation thread">
        <span>+</span> New Chat
      </a>
    </div>
  </header>

  <!-- Main Container (Fixed Viewport Height) -->
  <main class="app-main">
    
    <!-- Left Sidebar: Client Context & Quick Prompts (Scrolls independently) -->
    <aside class="sidebar">
      
      <!-- Client Profile & Scope Guard Info -->
      <div class="side-card">
        <div class="side-card-title">
          <span>Active Organization</span>
        </div>
        <div class="client-profile-box">
          <div class="client-name">
            <?= $client_id === 'C-01' ? 'Northwind Utilities' : 'Blue Delta Infra' ?>
            <span class="client-id-pill"><?= html_escape($client_id) ?></span>
          </div>
          <div class="client-meta">
            <?= $client_id === 'C-01'
              ? 'Authorized for smart grid, water metering, and clean tech market research.'
              : 'Authorized for civil infrastructure, transit systems, and structural asset reports.' ?>
          </div>
          <div class="client-tags">
            <?php if ($client_id === 'C-01'): ?>
              <span class="tag">Smart Water</span>
              <span class="tag">Energy</span>
              <span class="tag">R-101 / R-102</span>
            <?php else: ?>
              <span class="tag">Civil Infra</span>
              <span class="tag">Transit</span>
              <span class="tag">R-300 Series</span>
            <?php endif; ?>
          </div>
        </div>
      </div>

      <!-- Quick Suggested Prompts -->
      <div class="side-card">
        <div class="side-card-title">
          <span>Suggested Questions</span>
        </div>
        <div class="prompts-list">
          <?php if ($client_id === 'C-01'): ?>
            <button type="button" class="prompt-chip" onclick="fillPrompt(this.dataset.prompt)" data-prompt="What was the 2024 global smart water meter market size according to R-101 and R-102?">
              What was the 2024 smart water meter market size?
            </button>
            <button type="button" class="prompt-chip" onclick="fillPrompt(this.dataset.prompt)" data-prompt="Compare the scope between R-101 and R-102.">
              Compare the scope of R-101 and R-102
            </button>
            <button type="button" class="prompt-chip" onclick="fillPrompt(this.dataset.prompt)" data-prompt="What is the projected 2029 market size in R-101 and R-102?">
              Projected 2029 market size in R-101 & R-102?
            </button>
            <button type="button" class="prompt-chip" onclick="fillPrompt(this.dataset.prompt)" data-prompt="Which sector has the most reports in your library?">
              Which sector has the most reports?
            </button>
          <?php else: ?>
            <button type="button" class="prompt-chip" onclick="fillPrompt(this.dataset.prompt)" data-prompt="Which sector has the most reports in your library?">
              Which sector has the most reports?
            </button>
            <button type="button" class="prompt-chip" onclick="fillPrompt(this.dataset.prompt)" data-prompt="What reports are available in my authorized infrastructure sector?">
              What reports are in my infrastructure scope?
            </button>
            <button type="button" class="prompt-chip" onclick="fillPrompt(this.dataset.prompt)" data-prompt="What was the 2024 global smart water meter market size?">
              Test out-of-scope report boundary (R-101)
            </button>
          <?php endif; ?>
        </div>
      </div>

      <!-- Grounding Guard Policy -->
      <div class="side-card">
        <div class="side-card-title">
          <span>Enterprise Grounding Rules</span>
        </div>
        <p style="font-size: 0.78rem; color: var(--text-muted); line-height: 1.45;">
          • Multi-report market differences are kept distinct rather than averaged.<br>
          • Derived calculations (CAGR, variances) are explicitly flagged.<br>
          • Strict client boundary enforcement ensures multi-tenant isolation.<br>
          • Low-confidence queries automatically escalate to senior analysts.
        </p>
      </div>

    </aside>

    <!-- Center Workspace: Chat History & Docked Bottom Composer -->
    <section class="chat-section">
      
      <div class="chat-card">

        <!-- Inner Chat Scroll Area (ONLY THIS SCROLLS) -->
        <div class="chat-scroll-area" id="chat-scroll-area">
          
          <!-- Thread messages -->
          <div class="thread-container" id="thread-container">
            <?php if (empty($history) && empty($result)): ?>
              <div class="empty-state">
                <div class="empty-icon">📊</div>
                <div class="empty-title">Welcome to Report Copilot</div>
                <p class="empty-desc">
                  Ask specific questions about market sizes, growth projections, scopes, and cross-report comparisons. Atlas synthesizes verified insights directly from published analyst reports.
                </p>
              </div>
            <?php endif; ?>

            <!-- Chronological History Messages -->
            <?php if (!empty($history)): ?>
              <?php foreach ($history as $idx => $entry): ?>
                <div class="message-row <?= $entry['role'] === 'user' ? 'user' : 'assistant' ?>">
                  <div class="avatar <?= $entry['role'] === 'user' ? 'user-avatar' : 'ai-avatar' ?>">
                    <?= $entry['role'] === 'user' ? '👤' : 'A' ?>
                  </div>
                  <div class="bubble">
                    <div class="bubble-header">
                      <span><?= $entry['role'] === 'user' ? 'You' : 'Atlas Copilot' ?></span>
                      <?php if (!empty($entry['created_at'])): ?>
                        <span><?= html_escape(date('H:i', strtotime($entry['created_at']))) ?></span>
                      <?php endif; ?>
                    </div>
                    <div class="bubble-content"><?= html_escape($entry['content']) ?></div>
                    <?php if ($entry['role'] === 'assistant'): ?>
                      <div class="bubble-actions">
                        <button type="button" class="btn-copy" onclick="copyContent(this)">
                          📋 Copy text
                        </button>
                      </div>
                    <?php endif; ?>
                  </div>
                </div>
              <?php endforeach; ?>
            <?php endif; ?>
          </div>

          <!-- Latest Result: Answer / Notice / Metadata -->
          <?php if (is_array($result) && !empty($result['answer'])): ?>
            
            <?php if (isset($result['confidence'])): ?>
              <!-- Standard Grounded Answer Card -->
              <div class="answer-card" id="latest-response">
                <div class="answer-card-header">
                  <span class="brand-icon" style="width:22px;height:22px;font-size:0.8rem;">A</span>
                  <span>Atlas Copilot Answer</span>
                </div>
                <div class="answer-card-body"><?= html_escape($result['answer']) ?></div>
              </div>

              <!-- Full Metadata Inspector (Confidence, Citations, Conflicts, Derived, Feedback) -->
              <div class="result-inspector">
                
                <!-- Header bar with confidence & escalation -->
                <div class="inspector-header">
                  <div class="confidence-meter">
                    <span class="confidence-label">Confidence</span>
                    <?php
                      $confScore = round(($result['confidence'] ?? 0) * 100);
                      $barClass = $confScore >= 85 ? 'high' : ($confScore >= 60 ? 'medium' : 'low');
                    ?>
                    <div class="confidence-track">
                      <div class="confidence-bar <?= $barClass ?>" style="width: <?= $confScore ?>%;"></div>
                    </div>
                    <span class="confidence-val"><?= $confScore ?>%</span>
                  </div>

                  <div>
                    <?php if (!empty($result['escalated'])): ?>
                      <span class="escalation-badge escalated">
                        ⚠️ Escalated to Senior Analyst
                      </span>
                    <?php else: ?>
                      <span class="escalation-badge verified">
                        ✓ Verified Grounded Answer
                      </span>
                      <?php if (!empty($result['cached'])): ?>
                        <span class="escalation-badge" style="background:#f0fdf4; color:#166534; border:1px solid #bbf7d0; margin-left:0.4rem;">
                          ⚡ Cached (0ms)
                        </span>
                      <?php endif; ?>
                    <?php endif; ?>
                  </div>
                </div>

                <!-- Citations -->
                <?php if (!empty($result['citations'])): ?>
                  <div class="citations-section">
                    <h4>📑 Verified Sources (<?= count($result['citations']) ?>)</h4>
                    <div class="citation-cards">
                      <?php foreach ($result['citations'] as $cit): ?>
                        <div class="citation-card">
                          <div class="citation-pills">
                            <span class="report-id-pill"><?= html_escape($cit['report_id'] ?? '') ?></span>
                            <span class="page-pill">Page <?= html_escape((string)($cit['page'] ?? '')) ?></span>
                          </div>
                          <div class="citation-title"><?= html_escape($cit['report_title'] ?? '') ?></div>
                          <?php if (!empty($cit['snippet'])): ?>
                            <div class="citation-snippet">“<?= html_escape($cit['snippet']) ?>”</div>
                          <?php endif; ?>
                        </div>
                      <?php endforeach; ?>
                    </div>
                  </div>
                <?php endif; ?>

                <!-- Conflicts -->
                <?php if (!empty($result['conflicts'])): ?>
                  <div class="conflicts-section">
                    <div class="conflict-callout">
                      <span style="font-size: 1.1rem;">⚠️</span>
                      <div>
                        <strong>Report Conflict Detected</strong>
                        <p style="font-size: 0.8rem; margin-top: 0.2rem;">
                          Discrepancies identified across published reports. Values are retained as published:
                        </p>
                        <ul>
                          <?php foreach ($result['conflicts'] as $conflict): ?>
                            <li><?= html_escape($conflict) ?></li>
                          <?php endforeach; ?>
                        </ul>
                      </div>
                    </div>
                  </div>
                <?php endif; ?>

                <!-- Derived Values -->
                <?php if (!empty($result['derived_values'])): ?>
                  <div class="derived-section">
                    <h4>🧮 Derived Computations</h4>
                    <div class="derived-grid">
                      <?php foreach ($result['derived_values'] as $derived): ?>
                        <span class="derived-chip">
                          <?= html_escape(is_array($derived) ? json_encode($derived, JSON_UNESCAPED_SLASHES) : (string)$derived) ?>
                        </span>
                      <?php endforeach; ?>
                    </div>
                  </div>
                <?php endif; ?>

                <!-- Feedback Rating Form -->
                <?php if (!empty($result['message_id']) && !empty($result['conversation_id'])): ?>
                  <div class="feedback-row">
                    <span>Was this response helpful and accurate?</span>
                    <form class="feedback-buttons" method="post" action="/copilot/feedback">
                      <?= form_hidden($this->security->get_csrf_token_name(), $this->security->get_csrf_hash()) ?>
                      <input type="hidden" name="message_id" value="<?= (int)$result['message_id'] ?>">
                      <input type="hidden" name="conversation_id" value="<?= html_escape($result['conversation_id']) ?>">
                      <button type="submit" name="rating" value="1" class="btn-rating up" title="Helpful answer">
                        👍 Helpful
                      </button>
                      <button type="submit" name="rating" value="-1" class="btn-rating down" title="Unhelpful or inaccurate">
                        👎 Inaccurate
                      </button>
                    </form>
                  </div>
                <?php endif; ?>

              </div>

            <?php else: ?>
              <!-- Service Notice / Rate-limit Banner -->
              <div class="notice-card" id="latest-response">
                <div class="notice-card-header">
                  <span>⏳</span>
                  <span>System Notice / Rate Limit</span>
                </div>
                <div class="notice-card-body">
                  <?= html_escape($result['answer']) ?>
                </div>
                <div class="notice-card-help">
                  Notice: Groq's daily rolling token quota (200k tokens) is currently near capacity. The service automatically backs off and resumes once the rolling quota window clears.
                </div>
              </div>
            <?php endif; ?>

          <?php endif; ?>

        </div>

        <!-- Fixed Bottom Composer Container (NEVER SCROLLS) -->
        <div class="composer-container">
          
          <!-- Loading spinner state -->
          <div class="loading-overlay" id="loading-overlay">
            <div class="spinner"></div>
            <span>Synthesizing answer, checking entitlements & verifying citations...</span>
          </div>

          <!-- Composer Form -->
          <form class="composer-form" id="chat-form" method="post" action="/copilot/chat" onsubmit="handleFormSubmit()">
            <?= form_hidden($this->security->get_csrf_token_name(), $this->security->get_csrf_hash()) ?>
            <input type="hidden" name="client_id" value="<?= html_escape($client_id) ?>">

            <div class="composer-wrapper">
              <textarea
                id="message-input"
                name="message"
                class="composer-textarea"
                placeholder="Ask about market size, projections, scopes, or report comparisons... (Press Ctrl+Enter to send)"
                maxlength="4000"
                required
                rows="2"
                oninput="handleInput(this)"
                onkeydown="handleKeydown(event)"
              ></textarea>

              <div class="composer-footer">
                <span class="char-count" id="char-count">0 / 4,000 characters</span>
                <div class="composer-actions">
                  <button type="submit" class="btn-submit" id="btn-submit">
                    <span>Ask Copilot</span>
                    <span>➔</span>
                  </button>
                </div>
              </div>
            </div>
          </form>

        </div>

      </div>

    </section>

  </main>

  <script>
    // Scroll chat container to bottom on load
    window.addEventListener('DOMContentLoaded', () => {
      const scrollArea = document.getElementById('chat-scroll-area');
      if (scrollArea) {
        scrollArea.scrollTop = scrollArea.scrollHeight;
      }
    });

    // Populate suggested prompt
    function fillPrompt(text) {
      const input = document.getElementById('message-input');
      if (input) {
        input.value = text;
        handleInput(input);
        input.focus();
      }
    }

    // Auto-resize textarea & character count
    function handleInput(textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 140) + 'px';
      const countEl = document.getElementById('char-count');
      if (countEl) {
        countEl.textContent = textarea.value.length.toLocaleString() + ' / 4,000 characters';
      }
    }

    // Ctrl+Enter or Cmd+Enter to submit
    function handleKeydown(event) {
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        const form = document.getElementById('chat-form');
        if (form && event.target.value.trim().length > 0) {
          form.requestSubmit();
        }
      }
    }

    // Show loading state on form submit
    function handleFormSubmit() {
      const btn = document.getElementById('btn-submit');
      const loader = document.getElementById('loading-overlay');
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span>Processing...</span>';
      }
      if (loader) {
        loader.style.display = 'flex';
      }
      const scrollArea = document.getElementById('chat-scroll-area');
      if (scrollArea) {
        scrollArea.scrollTop = scrollArea.scrollHeight;
      }
    }

    // Copy response text
    function copyContent(btn) {
      const bubble = btn.closest('.bubble');
      if (!bubble) return;
      const content = bubble.querySelector('.bubble-content');
      if (!content) return;
      navigator.clipboard.writeText(content.innerText).then(() => {
        const originalText = btn.innerHTML;
        btn.innerHTML = '✓ Copied!';
        setTimeout(() => {
          btn.innerHTML = originalText;
        }, 2000);
      });
    }
  </script>
</body>
</html>
