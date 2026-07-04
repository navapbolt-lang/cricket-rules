(function () {
  'use strict';

  var API_BASE = '/api/v1';
  var PARTNER_ID = '';
  var API_KEY = '';

  var $ = function (id) { return document.getElementById(id); };

  function show(id) { $(id).classList.remove('hidden'); }
  function hide(id) { $(id).classList.add('hidden'); }

  // ── Login ──
  $('login-btn').addEventListener('click', login);
  $('api-key-input').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') login();
  });

  function login() {
    var key = $('api-key-input').value.trim();
    if (!key) { $('login-error').textContent = 'Please enter your API key.'; return; }
    API_KEY = key;
    fetch(API_BASE + '/suggestions?context=general', {
      headers: { 'X-API-Key': key }
    }).then(function (r) {
      if (r.ok) {
        PARTNER_ID = 'partner';
        hide('login-view');
        show('dashboard-view');
        $('login-error').textContent = '';
        sessionStorage.setItem('cr_admin_key', key);
        loadDashboard();
      } else if (r.status === 401) {
        $('login-error').textContent = 'Invalid API key.';
      } else {
        $('login-error').textContent = 'Server error. Try again.';
      }
    }).catch(function () {
      $('login-error').textContent = 'Cannot reach server.';
    });
  }

  $('logout-btn').addEventListener('click', function () {
    PARTNER_ID = '';
    API_KEY = '';
    sessionStorage.removeItem('cr_admin_key');
    hide('dashboard-view');
    show('login-view');
    $('api-key-input').value = '';
  });

  // ── Tab switching ──
  document.querySelectorAll('.tab-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.tab-btn').forEach(function (b) { b.classList.remove('active'); });
      document.querySelectorAll('.tab-content').forEach(function (c) { c.classList.remove('active'); });
      btn.classList.add('active');
      $(btn.dataset.tab).classList.add('active');
    });
  });

  // ── Copy embed code ──
  $('copy-embed-btn').addEventListener('click', function () {
    var code = $('embed-code');
    if (!code.textContent.trim()) return;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(code.textContent).then(function () {
        $('copy-embed-btn').textContent = 'Copied!';
        setTimeout(function () { $('copy-embed-btn').textContent = 'Copy to Clipboard'; }, 2000);
      });
    } else {
      var range = document.createRange();
      range.selectNode(code);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);
      document.execCommand('copy');
      $('copy-embed-btn').textContent = 'Copied!';
      setTimeout(function () { $('copy-embed-btn').textContent = 'Copy to Clipboard'; }, 2000);
    }
  });

  // ── Dashboard ──
  function loadDashboard() {
    var base = window.location.origin;
    $('embed-code').textContent =
      '<script src="' + base + '/widget/embed.js" data-partner="' + PARTNER_ID + '" data-brand-color="#1a1a2e" data-position="right"><\/script>';

    loadStats();
    loadTopQueries();
  }

  function apiGet(path) {
    return fetch(API_BASE + path, { headers: { 'X-API-Key': API_KEY } }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function loadStats() {
    apiGet('/stats/overview').then(function (data) {
      var daily = data.daily || {};
      $('stat-queries').textContent = daily.total != null ? daily.total : '—';
      $('stat-confidence').textContent = daily.avg_confidence != null ? (daily.avg_confidence * 100).toFixed(0) + '%' : '—';
      $('stat-latency').textContent = daily.avg_latency_ms != null ? daily.avg_latency_ms.toFixed(0) : '—';
      $('set-partner-id').textContent = PARTNER_ID;
      $('set-plan').textContent = 'Starter';
      $('set-quota').textContent = '10,000 / month';

      var chart = $('format-chart');
      var fmt = daily.by_format || {};
      var keys = Object.keys(fmt);
      if (keys.length > 0) {
        chart.innerHTML = '';
        keys.forEach(function (k) {
          var div = document.createElement('div');
          div.className = 'format-bar';
          div.innerHTML = '<div class="label">' + k + '</div><div class="value">' + fmt[k] + '</div>';
          chart.appendChild(div);
        });
      } else {
        chart.innerHTML = '<div class="empty-state">No format data yet. Start chatting to see breakdown.</div>';
      }
    }).catch(function () {
      $('stat-queries').textContent = '—';
      $('stat-confidence').textContent = '—';
      $('stat-latency').textContent = '—';
      $('set-partner-id').textContent = PARTNER_ID;
      $('set-plan').textContent = 'Starter';
      $('set-quota').textContent = '10,000 / month';
    });
  }

  function loadTopQueries() {
    apiGet('/stats/top-queries?limit=10').then(function (data) {
      var tbody = $('top-queries-body');
      var empty = $('queries-empty');
      tbody.innerHTML = '';
      var queries = data.queries || [];
      if (queries.length === 0) {
        empty.style.display = 'block';
        empty.textContent = 'No queries recorded yet. Start chatting to see data here.';
        return;
      }
      empty.style.display = 'none';
      queries.forEach(function (q) {
        var tr = document.createElement('tr');
        tr.innerHTML = '<td>' + escapeHtml(q.query || '—') + '</td><td>' + (q.count || 0) + '</td>';
        tbody.appendChild(tr);
      });
    }).catch(function () {
      $('queries-empty').style.display = 'block';
      $('queries-empty').textContent = 'Could not load query data.';
    });
  }

  function escapeHtml(text) {
    var d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
  }

  // ── Auto-login ──
  var stored = sessionStorage.getItem('cr_admin_key');
  if (stored) {
    $('api-key-input').value = stored;
    login();
  }
})();
