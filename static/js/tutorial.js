/**
 * Rangkai.click — Interactive Guided Tutorial ("Tur Praktik Rangkai")
 * Action -> Ripple Effect architecture, HTMX hx-boost compatible, role-aware,
 * with optional 1-click sample data & atomic surgical cleanup.
 */
(function () {
  'use strict';

  function getCsrfToken() {
    var dockWrap = document.getElementById('wp-tutorial-dock-wrap');
    if (dockWrap && dockWrap.dataset && dockWrap.dataset.csrf) {
      return dockWrap.dataset.csrf;
    }
    var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (input && input.value) return input.value;
    if (document.cookie) {
      var m = document.cookie.match(/(?:^|;\s*)(?:rangkai_csrftoken|csrftoken)=([^;]+)/);
      if (m) return decodeURIComponent(m[1]);
    }
    return '';
  }

  function normalizePath(path) {
    if (!path) return '/';
    if (path === '/dashboard/' || path === '/dashboard') return '/';
    return path.endsWith('/') ? path : path + '/';
  }

  function syncSidebarActiveLink(url) {
    var norm = normalizePath(url);
    document.querySelectorAll('#sidebar a[data-slot="sidebar-menu-button"]').forEach(function (a) {
      var href = a.getAttribute('href');
      if (!href) return;
      var linkNorm = normalizePath(href);
      a.classList.toggle('active', linkNorm === norm);
    });
  }

  function navigateSmooth(url) {
    var targetPath = normalizePath(url);
    var currentPath = normalizePath(window.location.pathname);
    if (targetPath === currentPath) {
      syncSidebarActiveLink(url);
      return Promise.resolve();
    }
    if (window.htmx && document.querySelector('.main-content')) {
      return new Promise(function (resolve) {
        var settled = false;
        function finish() {
          if (settled) return;
          settled = true;
          document.body.removeEventListener('htmx:afterSwap', onSwap);
          syncSidebarActiveLink(url);
          resolve();
        }
        function onSwap(evt) {
          var tgt = evt.detail && evt.detail.target;
          if (!tgt || tgt.classList.contains('main-content') || tgt.querySelector('.main-content')) {
            finish();
          }
        }
        document.body.addEventListener('htmx:afterSwap', onSwap);
        try {
          window.history.pushState({}, '', url);
        } catch (e) {}
        window.htmx.ajax('GET', url, {
          target: '.main-content',
          select: '.main-content',
          swap: 'outerHTML show:top'
        });
        setTimeout(finish, 2000);
      });
    }
    window.location.href = url;
    return Promise.resolve();
  }

  function reloadCurrentSmooth() {
    var url = window.location.pathname + window.location.search;
    if (window.htmx && document.querySelector('.main-content')) {
      return new Promise(function (resolve) {
        var settled = false;
        function finish() {
          if (settled) return;
          settled = true;
          document.body.removeEventListener('htmx:afterSwap', onSwap);
          resolve();
        }
        function onSwap(evt) {
          var tgt = evt.detail && evt.detail.target;
          if (!tgt || tgt.classList.contains('main-content') || tgt.querySelector('.main-content')) {
            finish();
          }
        }
        document.body.addEventListener('htmx:afterSwap', onSwap);
        window.htmx.ajax('GET', url, {
          target: '.main-content',
          select: '.main-content',
          swap: 'outerHTML show:none'
        });
        setTimeout(finish, 2000);
      });
    }
    window.location.reload();
    return Promise.resolve();
  }

  // Mission catalog with Action phase + multi-stop Ripple Effect (Impact) phase
  var ALL_MISSIONS = [
    {
      key: 'savings',
      requires: 'can_access_savings',
      moduleLabel: 'Tabungan Bersama',
      route: '/budgets/savings/',
      eventKey: 'savings_saved',
      actionTitle: 'Atur Target Tabungan & Setoran',
      actionDesc: 'Isi target tabungan atau tambah 1 setoran di kotak yang disorot. Mau langsung lihat simulasi cepat? Klik "Pakai Data Contoh".',
      actionSelectors: ['#guide-savings-target'],
      sampleLabel: 'Pakai Data Contoh (Rp 150 jt)',
      impacts: [
        {
          route: '/budgets/savings/',
          title: 'Progres & Estimasi Tercapai Langsung Terhitung',
          desc: 'Dari target & setoran tadi, Rangkai langsung menghitung sisa dana, persentase terkumpul, estimasi bulan tercapai, dan grafik akumulasi.',
          callout: 'Tabungan Bersama 100% privat — hanya bisa dilihat oleh Pengantin (Owner & Co-Owner).',
          selectors: ['#guide-savings-progress', '#guide-savings-chart']
        },
        {
          route: '/budgets/',
          title: 'Efek Domino: Otomatis Jadi Pagu Anggaran!',
          desc: 'Target tabungan yang tadi diisi langsung masuk sebagai Total Budget di halaman Anggaran & Kas, sehingga alokasi tiap kategori otomatis terbagi.',
          callout: 'Cukup atur sekali di Tabungan, alokasi Anggaran langsung siap dipakai.',
          selectors: ['#guide-budget-summary']
        }
      ]
    },
    {
      key: 'budget',
      requires: 'can_access_finance',
      moduleLabel: 'Anggaran & Kas',
      route: '/budgets/',
      eventKey: 'budget_saved',
      actionTitle: 'Catat 1 Pengeluaran Pertama',
      actionDesc: 'Tambahkan 1 item pengeluaran di salah satu kategori (misal DP Venue + tanggal jatuh tempo), atau klik "Pakai Data Contoh".',
      actionSelectors: ['#guide-categories'],
      sampleLabel: 'Pakai Data Contoh (DP Venue)',
      impacts: [
        {
          route: '/budgets/',
          title: 'Sisa Anggaran & Split Bill Langsung Terupdate',
          desc: 'Item yang baru dicatat otomatis memotong sisa anggaran, menghitung selisih (variance), dan membagi porsi bayar di Split Bill.',
          callout: 'Tidak perlu rumus Excel — setiap DP atau cicilan otomatis menghitung sisa termin.',
          selectors: ['#guide-budget-summary', '#guide-split-bill']
        },
        {
          route: '/',
          title: 'Efek Domino: Muncul di Ringkasan & Pengingat!',
          desc: 'Kartu "Sisa Ruang Anggaran" langsung bergerak, dan item yang jatuh temponya dekat otomatis muncul di "Jadwal Pembayaran Perlu Tindak Lanjut".',
          callout: 'Dari Ringkasan, kamu bisa langsung klik "Tandai Lunas" dalam 1 klik.',
          selectors: ['#guide-budget-rem', '#guide-attention']
        }
      ]
    },
    {
      key: 'vendors',
      requires: 'can_access_vendors',
      moduleLabel: 'Direktori Vendor',
      route: '/vendors/',
      eventKey: 'vendor_saved',
      actionTitle: 'Tambah 1 Kandidat Vendor',
      actionDesc: 'Tambah 1 kandidat vendor beserta skor Harga, Kualitas, Fasilitas & Reputasi, atau klik "Pakai Data Contoh".',
      actionSelectors: ['#guide-vendor-cards'],
      sampleLabel: 'Pakai Data Contoh (Studio Foto)',
      impacts: [
        {
          route: '/vendors/',
          title: 'Weighted Score Otomatis Menentukan Rekomendasi',
          desc: 'Rangkai menghitung skor objektif 0–100 sesuai bobot prioritasmu. Jika bobot Harga/Kualitas digeser, urutan rekomendasi vendor langsung menyesuaikan.',
          callout: 'Memudahkan kamu membandingkan 3–5 vendor per kategori secara objektif.',
          selectors: ['#guide-vendor-cards']
        }
      ]
    },
    {
      key: 'guests',
      requires: null,
      moduleLabel: 'Tamu & Katering',
      route: '/guests/',
      eventKey: 'guest_saved',
      actionTitle: 'Tambah 1 Tamu Undangan',
      actionDesc: 'Masukkan 1 tamu beserta jumlah pax & status RSVP "Hadir", atau klik "Pakai Data Contoh" (Keluarga Pak Budi · 4 pax VIP Hadir).',
      actionSelectors: ['#guide-guest-db'],
      sampleLabel: 'Pakai Data Contoh (4 Pax VIP)',
      impacts: [
        {
          route: '/guests/',
          title: 'Catering Simulator & Kuota 4-Arah Langsung Berubah',
          desc: 'Tamu yang baru masuk otomatis meng-update estimasi porsi prasmanan vs gubukan (plus safety buffer) dan keseimbangan kuota Keluarga vs Teman.',
          callout: 'Bisa juga import massal dari Excel & check-in tamu langsung dari HP saat Hari-H.',
          selectors: ['#guide-catering', '#guide-guest-quota']
        },
        {
          route: '/',
          title: 'Efek Domino: Konfirmasi Tamu di Ringkasan Naik!',
          desc: 'Setiap tamu berstatus "Hadir" langsung terakumulasi di kartu Konfirmasi Tamu di Ringkasan (jumlah undangan & total pax).',
          callout: 'Pasangan dan panitia selalu melihat angka tamu terbaru yang sama.',
          selectors: ['#guide-rsvp']
        }
      ]
    },
    {
      key: 'tasks',
      requires: null,
      moduleLabel: 'Daftar Tugas & Kalender',
      route: '/checklist/',
      eventKey: 'task_saved',
      actionTitle: 'Centang 1 Tugas Fase Aktif',
      actionDesc: 'Klik kotak centang pada salah satu tugas di daftar yang disorot untuk menandainya selesai, atau klik "Centang 1 Tugas Contoh".',
      actionSelectors: ['#task-list-section'],
      sampleLabel: 'Centang 1 Tugas Contoh',
      impacts: [
        {
          route: '/',
          title: 'Efek Domino: Kesiapan Tugas (%) di Ringkasan Naik!',
          desc: 'Mencentang tugas langsung menaikkan progress bar "Kesiapan Tugas" dan memperbarui daftar "Fokus Persiapan Saat Ini" secara real-time.',
          callout: 'Seluruh tim (pasangan, WO, crew) langsung melihat progres terbaru.',
          selectors: ['#guide-task-prog', '#guide-active-tasks']
        },
        {
          route: '/calendar/',
          title: 'Sinkron dengan Kalender Fase H-Minus',
          desc: 'Semua fase tugas dan deadline juga terpetakan otomatis di Kalender berdasarkan hitung mundur menuju tanggal pernikahanmu.',
          callout: 'Selesai! Klik tombol di bawah untuk menyelesaikan tur & membersihkan data contoh.',
          selectors: ['.cal-status-bar', '.cal-card']
        }
      ]
    }
  ];

  function clearHighlights() {
    document.querySelectorAll('.wp-tut-highlight').forEach(function (el) {
      el.classList.remove('wp-tut-highlight', 'wp-tut-highlight-impact');
    });
  }

  function applyHighlights(selectors, isImpact) {
    clearHighlights();
    if (!selectors || !selectors.length) return;
    var firstEl = null;
    for (var i = 0; i < selectors.length; i++) {
      var el = document.querySelector(selectors[i]);
      if (el) {
        el.classList.add('wp-tut-highlight');
        if (isImpact) el.classList.add('wp-tut-highlight-impact');
        if (!firstEl) firstEl = el;
      }
    }
    if (firstEl) {
      setTimeout(function () {
        try {
          firstEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } catch (e) {}
      }, 120);
    }
  }

  function refreshIcons() {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      try {
        window.lucide.createIcons();
      } catch (e) {}
    }
  }

  function showToast(msg, type) {
    var container = document.getElementById('wp-toast-container');
    if (!container || !msg) return;
    var el = document.createElement('div');
    el.className = 'message-toast ' + (type || 'success');
    el.innerHTML = '<span></span><button type="button" style="background:transparent;border:0;color:currentColor;opacity:0.65;cursor:pointer;padding:2px;display:inline-flex;align-items:center;" aria-label="Tutup">&times;</button>';
    el.querySelector('span').textContent = msg;
    el.querySelector('button').onclick = function () { el.remove(); };
    container.appendChild(el);
    setTimeout(function () { if (el.parentNode) el.remove(); }, 4500);
  }

  function apiPostJson(url, payload) {
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify(payload || {})
    }).then(function (r) {
      if (!r.ok) {
        throw new Error('HTTP ' + r.status);
      }
      return r.json();
    });
  }

  window.rangkaiTutorialComponent = function (initialData) {
    return {
      status: (initialData && initialData.status) || 'not_started',
      stepIndex: (initialData && initialData.step) || 0,
      phase: (initialData && initialData.phase) || 'action', // 'action' | 'impact' | 'summary' | 'confirm_exit'
      impactIndex: 0,
      currentPath: normalizePath(window.location.pathname),
      completedMissions: (initialData && initialData.completed_missions) || [],
      hasSampleData: !!(initialData && initialData.has_sample_data),
      sampleCount: (initialData && initialData.sample_count) || 0,
      roleFlags: {
        can_access_savings: !!(initialData && initialData.can_access_savings),
        can_access_finance: !!(initialData && initialData.can_access_finance),
        can_access_vendors: !!(initialData && initialData.can_access_vendors)
      },
      minimized: false,
      loadingSample: false,
      loadingCleanup: false,
      missions: [],

      get isActive() {
        return this.status === 'in_progress';
      },

      get currentMission() {
        if (!this.missions.length) return null;
        var idx = Math.min(this.stepIndex, this.missions.length - 1);
        return this.missions[idx] || null;
      },

      get currentImpact() {
        var m = this.currentMission;
        if (!m || !m.impacts || !m.impacts.length) return null;
        return m.impacts[Math.min(this.impactIndex, m.impacts.length - 1)] || null;
      },

      get onExpectedRoute() {
        if (this.phase === 'summary' || this.phase === 'confirm_exit') return true;
        var expected = this.phase === 'impact' && this.currentImpact
          ? this.currentImpact.route
          : (this.currentMission ? this.currentMission.route : '/');
        return this.currentPath === normalizePath(expected);
      },

      get nextImpactLabel() {
        var m = this.currentMission;
        if (!m) return 'Lanjut';
        if (this.impactIndex + 1 < m.impacts.length) {
          var nextStop = m.impacts[this.impactIndex + 1];
          if (normalizePath(nextStop.route) !== this.currentPath) {
            if (nextStop.route === '/') return 'Lihat efeknya di Ringkasan →';
            if (nextStop.route === '/budgets/') return 'Lihat sinkronisasi di Anggaran →';
            if (nextStop.route === '/calendar/') return 'Lihat di Kalender Fase →';
          }
          return 'Lihat dampak berikutnya →';
        }
        if (this.stepIndex + 1 < this.missions.length) {
          return 'Lanjut: ' + this.missions[this.stepIndex + 1].moduleLabel + ' →';
        }
        return 'Selesaikan Tur Praktik →';
      },

      init() {
        var self = this;
        this.missions = ALL_MISSIONS.filter(function (m) {
          if (!m.requires) return true;
          return !!self.roleFlags[m.requires];
        });
        if (this.stepIndex >= this.missions.length && this.missions.length > 0) {
          this.stepIndex = 0;
        }
        if (this.phase === 'confirm_exit') {
          this.phase = 'action';
        }

        // Re-render Lucide icons whenever phase or sample flag changes inside dock
        this.$watch('phase', function () {
          self.$nextTick(refreshIcons);
        });
        this.$watch('hasSampleData', function () {
          self.$nextTick(refreshIcons);
        });
        this.$watch('minimized', function () {
          self.$nextTick(refreshIcons);
        });

        // Global API for buttons in Dashboard, Guide, Settings, Sidebar
        window.RangkaiTutorial = {
          start: function () { self.startTour(false); },
          restart: function () { self.startTour(true); },
          resume: function () { self.minimized = false; self.goToCurrentTarget(); },
          dismiss: function () { self.dismissWelcome(); },
          cleanupOnly: function () { return self.cleanupSampleOnly(); },
          getState: function () {
            return {
              status: self.status,
              stepIndex: self.stepIndex,
              total: self.missions.length,
              hasSampleData: self.hasSampleData
            };
          }
        };
        window.startComprehensiveTour = function () { self.startTour(true); };

        // Listen for HTMX HX-Trigger tutorialEvent
        document.body.addEventListener('tutorialEvent', function (evt) {
          var action = evt.detail && evt.detail.action;
          if (action) self.handleDataEvent(action);
        });

        // Sync reactive path & re-apply highlights after HTMX navigation swaps
        document.body.addEventListener('htmx:afterSwap', function () {
          self.currentPath = normalizePath(window.location.pathname);
          if (self.isActive && !self.minimized) {
            setTimeout(function () { self.syncHighlights(); }, 140);
          }
        });

        window.addEventListener('popstate', function () {
          self.currentPath = normalizePath(window.location.pathname);
          if (self.isActive && !self.minimized) {
            setTimeout(function () { self.syncHighlights(); }, 140);
          }
        });

        // Check pending event from full-page redirect
        if (initialData && initialData.pending_event) {
          setTimeout(function () {
            self.handleDataEvent(initialData.pending_event);
          }, 180);
        } else if (this.isActive) {
          setTimeout(function () { self.syncHighlights(); }, 200);
        }

        this.updateSidebarBadge();
        this.$nextTick(refreshIcons);
      },

      updateSidebarBadge() {
        var badge = document.getElementById('wp-sidebar-tut-badge');
        if (!badge) return;
        if (this.isActive && this.missions.length > 0) {
          var stepNum = Math.min(this.stepIndex + 1, this.missions.length);
          badge.textContent = stepNum + '/' + this.missions.length;
          badge.style.display = 'inline-flex';
        } else {
          badge.style.display = 'none';
        }
      },

      syncState(extra) {
        var payload = Object.assign({
          status: this.status,
          step: this.stepIndex,
          phase: this.phase === 'confirm_exit' ? 'action' : this.phase
        }, extra || {});
        return apiPostJson('/tutorial/state/', payload)
          .then(function (data) {
            return (data && data.tutorial) ? data.tutorial : null;
          })
          .catch(function (err) {
            console.warn('[Tutorial] syncState error:', err);
            return null;
          });
      },

      startTour(reset) {
        this.status = 'in_progress';
        this.minimized = false;
        if (reset || this.stepIndex >= this.missions.length) {
          this.stepIndex = 0;
          this.completedMissions = [];
        }
        this.phase = 'action';
        this.impactIndex = 0;
        this.updateSidebarBadge();
        this.syncState({ reset: !!reset, status: 'in_progress', step: this.stepIndex, phase: 'action' });
        var banner = document.getElementById('wp-tutorial-welcome-card');
        if (banner) banner.style.display = 'none';
        this.goToCurrentTarget();
      },

      dismissWelcome() {
        this.status = 'dismissed';
        clearHighlights();
        this.updateSidebarBadge();
        var banner = document.getElementById('wp-tutorial-welcome-card');
        if (banner) banner.style.display = 'none';
        this.syncState({ status: 'dismissed' });
      },

      goToCurrentTarget() {
        var self = this;
        var targetUrl = '/';
        if (this.phase === 'impact' && this.currentImpact) {
          targetUrl = this.currentImpact.route;
        } else if (this.currentMission) {
          targetUrl = this.currentMission.route;
        }
        navigateSmooth(targetUrl).then(function () {
          self.currentPath = normalizePath(window.location.pathname);
          setTimeout(function () {
            self.syncHighlights();
            refreshIcons();
          }, 150);
        });
      },

      syncHighlights() {
        if (!this.isActive || this.minimized || this.phase === 'summary' || this.phase === 'confirm_exit') {
          clearHighlights();
          return;
        }
        if (!this.onExpectedRoute) {
          clearHighlights();
          return;
        }
        if (this.phase === 'impact' && this.currentImpact) {
          applyHighlights(this.currentImpact.selectors, true);
        } else if (this.currentMission) {
          applyHighlights(this.currentMission.actionSelectors, false);
        }
      },

      handleDataEvent(actionKey) {
        if (!this.isActive) return;
        var m = this.currentMission;
        if (!m || m.eventKey !== actionKey) return;
        if (this.completedMissions.indexOf(m.key) === -1) {
          this.completedMissions.push(m.key);
        }
        this.phase = 'impact';
        this.impactIndex = 0;
        this.minimized = false;
        this.syncState({ completed_mission: m.key, phase: 'impact' });
        this.goToCurrentTarget();
      },

      useSampleData() {
        var self = this;
        var m = this.currentMission;
        if (!m || this.loadingSample) return;
        this.loadingSample = true;
        apiPostJson('/tutorial/sample/', { mission: m.key })
          .then(function (data) {
            self.loadingSample = false;
            if (!data.ok) {
              showToast(data.message || 'Gagal membuat data contoh.', 'error');
              return;
            }
            if (data.tutorial) {
              self.hasSampleData = !!data.tutorial.has_sample_data;
              self.sampleCount = data.tutorial.sample_count || 0;
            } else {
              self.hasSampleData = true;
            }
            if (self.completedMissions.indexOf(m.key) === -1) {
              self.completedMissions.push(m.key);
            }
            showToast(data.message || 'Data contoh berhasil ditambahkan.', 'success');
            self.phase = 'impact';
            self.impactIndex = 0;
            self.syncState({ completed_mission: m.key, phase: 'impact' });
            var firstImpact = m.impacts && m.impacts[0];
            if (firstImpact && normalizePath(firstImpact.route) === self.currentPath) {
              reloadCurrentSmooth().then(function () {
                setTimeout(function () {
                  self.syncHighlights();
                  refreshIcons();
                }, 150);
              });
            } else {
              self.goToCurrentTarget();
            }
          })
          .catch(function (err) {
            console.warn('[Tutorial] useSampleData error:', err);
            self.loadingSample = false;
            showToast('Gagal menyiapkan data contoh. Silakan muat ulang halaman dan coba lagi.', 'error');
          });
      },

      prevImpact() {
        if (this.phase === 'impact' && this.impactIndex > 0) {
          this.impactIndex -= 1;
          this.goToCurrentTarget();
        }
      },

      nextImpactOrMission() {
        var m = this.currentMission;
        if (!m) return;
        if (this.phase === 'impact' && this.impactIndex + 1 < m.impacts.length) {
          this.impactIndex += 1;
          this.goToCurrentTarget();
          return;
        }
        if (this.stepIndex + 1 < this.missions.length) {
          this.stepIndex += 1;
          this.phase = 'action';
          this.impactIndex = 0;
          this.updateSidebarBadge();
          this.syncState({ step: this.stepIndex, phase: 'action' });
          this.goToCurrentTarget();
        } else {
          this.phase = 'summary';
          clearHighlights();
          this.syncState({ phase: 'summary' });
        }
      },

      skipCurrentMission() {
        if (this.stepIndex + 1 < this.missions.length) {
          this.stepIndex += 1;
          this.phase = 'action';
          this.impactIndex = 0;
          this.updateSidebarBadge();
          this.syncState({ step: this.stepIndex, phase: 'action' });
          this.goToCurrentTarget();
        } else {
          this.phase = 'summary';
          clearHighlights();
          this.syncState({ phase: 'summary' });
        }
      },

      requestExit() {
        if (this.hasSampleData && this.phase !== 'summary') {
          this.phase = 'confirm_exit';
          clearHighlights();
        } else {
          this.finishTour(false);
        }
      },

      cancelExit() {
        this.phase = 'action';
        this.syncHighlights();
      },

      cleanupSampleOnly() {
        var self = this;
        if (this.loadingCleanup) return Promise.resolve();
        this.loadingCleanup = true;
        return apiPostJson('/tutorial/cleanup/', {})
          .then(function (data) {
            self.loadingCleanup = false;
            self.hasSampleData = false;
            self.sampleCount = 0;
            showToast(data.message || 'Data contoh berhasil dibersihkan.', 'success');
            return reloadCurrentSmooth();
          })
          .catch(function (err) {
            console.warn('[Tutorial] cleanupSampleOnly error:', err);
            self.loadingCleanup = false;
            showToast('Gagal membersihkan data contoh. Coba muat ulang halaman.', 'error');
          });
      },

      cleanupAndFinish(markCompleted) {
        var self = this;
        if (this.loadingCleanup) return;
        this.loadingCleanup = true;
        var finalStatus = markCompleted ? 'completed' : 'dismissed';
        // Single atomic request: clean all sample data + finalize tutorial status
        apiPostJson('/tutorial/cleanup/', { finish_status: finalStatus })
          .then(function (data) {
            self.loadingCleanup = false;
            self.hasSampleData = false;
            self.sampleCount = 0;
            self.status = finalStatus;
            self.stepIndex = 0;
            self.phase = 'action';
            self.minimized = false;
            clearHighlights();
            self.updateSidebarBadge();
            showToast(data.message || 'Data contoh dibersihkan — workspace kamu siap dipakai!', 'success');
            // Return smoothly to Ringkasan (Dashboard) so the clean workspace is immediately visible
            if (self.currentPath === '/') {
              reloadCurrentSmooth();
            } else {
              navigateSmooth('/');
            }
          })
          .catch(function (err) {
            console.warn('[Tutorial] cleanupAndFinish error:', err);
            self.loadingCleanup = false;
            showToast('Gagal membersihkan data contoh. Coba muat ulang halaman.', 'error');
          });
      },

      finishTour(markCompleted) {
        var self = this;
        var finalStatus = markCompleted ? 'completed' : 'dismissed';
        this.status = finalStatus;
        this.phase = 'action';
        this.minimized = false;
        clearHighlights();
        this.updateSidebarBadge();
        this.syncState({ status: finalStatus, step: 0, phase: 'action' }).then(function () {
          if (markCompleted) {
            showToast('Tur Praktik selesai! Kamu bisa mengulangnya kapan saja di menu Panduan atau Pengaturan.', 'success');
            if (self.currentPath !== '/') {
              navigateSmooth('/');
            }
          }
        });
      },

      toggleMinimize() {
        this.minimized = !this.minimized;
        if (this.minimized) {
          clearHighlights();
        } else {
          this.syncHighlights();
        }
      }
    };
  };
})();
